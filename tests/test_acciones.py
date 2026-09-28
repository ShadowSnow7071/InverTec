from datetime import timedelta
from decimal import Decimal

import pytest

from backend.conexion import db
from backend.modelos import Cotizacion
from backend.servicios.acciones import CATALOGO, PRECIOS_BASE, AccionServicio


@pytest.fixture(autouse=True)
def _con_api_key(monkeypatch):
    # Se simula tener MARKET_DATA_API_KEY para ejercitar la ruta de refresco real.
    monkeypatch.setenv("MARKET_DATA_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(AccionServicio, "_PAUSA_ENTRE_PETICIONES", 0)


def _sembrar(**cambios_por_ticker):
    """Crea las 9 filas de cotizacion como lo hace la migración (simuladas)."""
    for ticker, precio in PRECIOS_BASE.items():
        db.session.add(Cotizacion(ticker=ticker, precio=Decimal(precio)))
    db.session.commit()
    for ticker, campos in cambios_por_ticker.items():
        fila = db.session.get(Cotizacion, ticker)
        for campo, valor in campos.items():
            setattr(fila, campo, valor)
    db.session.commit()


def _hace(**kwargs):
    return AccionServicio._ahora() - timedelta(**kwargs)


def test_vigencia_por_defecto_es_12_horas():
    assert AccionServicio._vigencia_segundos() == 60 * 60 * 12


def test_vigencia_es_configurable_por_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_CACHE_SEGUNDOS", "300")
    assert AccionServicio._vigencia_segundos() == 300


def test_reintento_por_defecto_es_15_minutos_y_configurable(monkeypatch):
    assert AccionServicio._reintento_segundos() == 60 * 15
    monkeypatch.setenv("MARKET_DATA_REINTENTO_SEGUNDOS", "60")
    assert AccionServicio._reintento_segundos() == 60


def test_sin_filas_en_bd_se_usa_la_referencia_simulada(app):
    cotizacion = AccionServicio._cotizacion("AAPL")

    assert cotizacion["precio"] == PRECIOS_BASE["AAPL"]
    assert cotizacion["real"] is False
    assert cotizacion["actualizado_en"] is None


def test_fila_sembrada_sin_dato_real_se_marca_como_simulada(app):
    _sembrar()

    cotizacion = AccionServicio._cotizacion("MSFT")

    assert cotizacion["precio"] == "426.75"
    assert cotizacion["real"] is False
    assert cotizacion["cambio_real"] is False


def test_lee_el_precio_real_guardado_en_la_bd(app):
    _sembrar(AAPL={"precio": Decimal("341.07"), "cambio_porcentaje": Decimal("1.53"), "actualizado_en": _hace(hours=1)})

    cotizacion = AccionServicio._cotizacion("AAPL")

    assert cotizacion["precio"] == "341.07"
    assert cotizacion["cambio_porcentaje"] == "1.53"
    assert cotizacion["real"] is True
    assert cotizacion["cambio_real"] is True


def test_todas_las_lecturas_ven_el_mismo_precio(app, client):
    # Regresión del bug de "341.07 en la tabla y 214.20 en el detalle": Mercado,
    # detalle, precio para Simular y cálculo de riesgo deben coincidir SIEMPRE.
    _sembrar(AAPL={"precio": Decimal("341.07"), "cambio_porcentaje": Decimal("1.53"), "actualizado_en": _hace(hours=1)})

    en_catalogo = next(a for a in AccionServicio.listar_catalogo() if a["ticker"] == "AAPL")
    en_detalle = AccionServicio.obtener_por_ticker("AAPL")
    en_riesgo = AccionServicio.calcular_riesgo("AAPL", "1", "50000")
    en_api_catalogo = next(a for a in client.get("/api/acciones").get_json() if a["ticker"] == "AAPL")
    en_api_detalle = client.get("/api/acciones/AAPL").get_json()
    en_api_precio = client.get("/api/acciones/AAPL/precio").get_json()

    precios = {
        en_catalogo["precio_actual"],
        en_detalle["precio_actual"],
        en_riesgo["precio_unitario"],
        en_api_catalogo["precio_actual"],
        en_api_detalle["precio_actual"],
        en_api_precio["precio_actual"],
    }
    assert precios == {"341.07"}


def test_el_detalle_expone_si_el_precio_es_real_y_su_fecha(app, client):
    _sembrar(AAPL={"precio": Decimal("341.07"), "actualizado_en": _hace(hours=1)})

    detalle = client.get("/api/acciones/AAPL").get_json()

    assert detalle["precio_real"] is True
    assert detalle["actualizado_en"].endswith("Z")


def test_refrescar_guarda_los_precios_reales_de_todo_el_catalogo(app, monkeypatch):
    _sembrar()
    monkeypatch.setattr(
        AccionServicio,
        "_cotizacion_externa",
        staticmethod(lambda ticker: {"precio": "305.50", "cambio_porcentaje": "1.20"}),
    )

    resumen = AccionServicio.refrescar_cotizaciones(forzar=True)

    assert sorted(resumen["actualizadas"]) == sorted(CATALOGO)
    assert resumen["fallidas"] == []
    cotizacion = AccionServicio._cotizacion("TSLA")
    assert cotizacion["precio"] == "305.50"
    assert cotizacion["real"] is True


def test_refrescar_no_pide_las_cotizaciones_que_siguen_vigentes(app, monkeypatch):
    _sembrar(**{ticker: {"actualizado_en": _hace(hours=1)} for ticker in CATALOGO})
    llamadas = []
    monkeypatch.setattr(
        AccionServicio,
        "_cotizacion_externa",
        staticmethod(lambda ticker: llamadas.append(ticker) or {"precio": "1.00", "cambio_porcentaje": "0.10"}),
    )

    resumen = AccionServicio.refrescar_cotizaciones()

    assert resumen["actualizadas"] == []
    assert llamadas == []


def test_refrescar_solo_pide_las_vencidas(app, monkeypatch):
    _sembrar(**{ticker: {"actualizado_en": _hace(hours=1)} for ticker in CATALOGO})
    fila = db.session.get(Cotizacion, "NVDA")
    fila.actualizado_en = _hace(hours=13)  # pasó la vigencia de 12 h
    db.session.commit()
    llamadas = []
    monkeypatch.setattr(
        AccionServicio,
        "_cotizacion_externa",
        staticmethod(lambda ticker: llamadas.append(ticker) or {"precio": "130.00", "cambio_porcentaje": "0.50"}),
    )

    resumen = AccionServicio.refrescar_cotizaciones()

    assert llamadas == ["NVDA"]
    assert resumen["actualizadas"] == ["NVDA"]


def test_un_fallo_no_pisa_el_dato_real_anterior(app, monkeypatch):
    anterior = _hace(hours=13)
    _sembrar(AAPL={"precio": Decimal("300.00"), "cambio_porcentaje": Decimal("0.80"), "actualizado_en": anterior})
    monkeypatch.setattr(AccionServicio, "_cotizacion_externa", staticmethod(lambda ticker: None))

    resumen = AccionServicio.refrescar_cotizaciones(forzar=True)

    assert resumen["fallidas"] == ["AAPL"]
    cotizacion = AccionServicio._cotizacion("AAPL")
    assert cotizacion["precio"] == "300.00"  # no volvió al simulado 214.20
    assert cotizacion["real"] is True


def test_el_primer_fallo_detiene_el_lote_para_no_gastar_peticiones(app, monkeypatch):
    _sembrar()
    llamadas = []
    monkeypatch.setattr(
        AccionServicio,
        "_cotizacion_externa",
        staticmethod(lambda ticker: llamadas.append(ticker)),  # devuelve None: límite agotado
    )

    resumen = AccionServicio.refrescar_cotizaciones(forzar=True)

    assert len(llamadas) == 1
    assert len(resumen["fallidas"]) == 1
    assert len(resumen["sin_intentar"]) == len(CATALOGO) - 1
    assert resumen["actualizadas"] == []


def test_el_reclamo_lo_gana_un_solo_worker(app):
    _sembrar()
    # Dos workers ven la misma foto "vieja" de la tabla al mismo tiempo.
    foto_worker_a = AccionServicio._leer_filas()
    foto_worker_b = AccionServicio._leer_filas()

    ganadas_a = AccionServicio._reclamar_vencidas(foto_worker_a)
    ganadas_b = AccionServicio._reclamar_vencidas(foto_worker_b)

    assert sorted(ganadas_a) == sorted(CATALOGO)
    assert ganadas_b == []  # el UPDATE atómico ya no encuentra nada por reclamar


def test_el_reclamo_respeta_la_espera_entre_reintentos(app):
    _sembrar(
        AAPL={"ultimo_intento_en": _hace(minutes=1)},
        MSFT={"ultimo_intento_en": _hace(hours=2)},
    )

    ganadas = AccionServicio._reclamar_vencidas(AccionServicio._leer_filas())

    assert "AAPL" not in ganadas  # se intentó hace 1 min: todavía no toca
    assert "MSFT" in ganadas


def test_el_reclamo_ignora_las_cotizaciones_vigentes(app):
    _sembrar(**{ticker: {"actualizado_en": _hace(hours=1)} for ticker in CATALOGO})

    assert AccionServicio._reclamar_vencidas(AccionServicio._leer_filas()) == []


def test_en_pruebas_listar_catalogo_no_dispara_refresco_en_segundo_plano(app):
    _sembrar()

    AccionServicio.listar_catalogo()

    filas = AccionServicio._leer_filas()
    assert all(fila.ultimo_intento_en is None for fila in filas.values())


def test_ultima_actualizacion_es_none_sin_datos_reales_y_la_fecha_mas_reciente_con_ellos(app):
    _sembrar()
    assert AccionServicio.ultima_actualizacion() is None

    reciente = _hace(minutes=5)
    fila = db.session.get(Cotizacion, "AAPL")
    fila.actualizado_en = reciente
    db.session.commit()

    assert AccionServicio.ultima_actualizacion() == reciente


def test_comando_cli_actualiza_cotizaciones(app, monkeypatch):
    _sembrar()
    monkeypatch.setattr(
        AccionServicio,
        "_cotizacion_externa",
        staticmethod(lambda ticker: {"precio": "200.00", "cambio_porcentaje": "0.25"}),
    )

    resultado = app.test_cli_runner().invoke(args=["actualizar-cotizaciones", "--forzar"])

    assert resultado.exit_code == 0
    assert "Actualizadas" in resultado.output
    assert AccionServicio._cotizacion("AMD")["precio"] == "200.00"


def test_comando_cli_sin_api_key_avisa_y_falla(app, monkeypatch):
    monkeypatch.delenv("MARKET_DATA_API_KEY", raising=False)

    resultado = app.test_cli_runner().invoke(args=["actualizar-cotizaciones"])

    assert resultado.exit_code == 1
    assert "MARKET_DATA_API_KEY" in resultado.output
