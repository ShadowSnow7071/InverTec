from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app
from sqlalchemy import func, or_, select, update

from backend.conexion import db
from backend.modelos import Cotizacion
from backend.servicios.auth import ErrorNegocio

CATALOGO = {
    "AAPL": {"nombre_empresa": "Apple Inc.", "volatilidad": "0.20"},
    "MSFT": {"nombre_empresa": "Microsoft", "volatilidad": "0.18"},
    "GOOGL": {"nombre_empresa": "Alphabet", "volatilidad": "0.19"},
    "NVDA": {"nombre_empresa": "NVIDIA", "volatilidad": "0.42"},
    "AMZN": {"nombre_empresa": "Amazon", "volatilidad": "0.24"},
    "META": {"nombre_empresa": "Meta", "volatilidad": "0.28"},
    "TSLA": {"nombre_empresa": "Tesla", "volatilidad": "0.55"},
    "NFLX": {"nombre_empresa": "Netflix", "volatilidad": "0.30"},
    "AMD": {"nombre_empresa": "AMD", "volatilidad": "0.43"},
}

PRECIOS_BASE = {
    "AAPL": "214.20",
    "MSFT": "426.75",
    "GOOGL": "178.90",
    "NVDA": "127.85",
    "AMZN": "192.30",
    "META": "490.50",
    "TSLA": "252.10",
    "NFLX": "643.20",
    "AMD": "165.45",
}


class AccionServicio:

    _VIGENCIA_SEGUNDOS_DEFECTO = 60 * 60 * 12
    _REINTENTO_SEGUNDOS_DEFECTO = 60 * 15
    _ENFRIAMIENTO_MANUAL_SEGUNDOS = 60 * 5
    _PAUSA_ENTRE_PETICIONES = 1.2

    @staticmethod
    def _segundos_de_entorno(nombre, defecto):

        try:
            valor = int(os.environ.get(nombre, "").strip())
        except ValueError:
            return defecto
        return valor if valor > 0 else defecto

    @classmethod
    def _vigencia_segundos(cls):
        # Misma variable de entorno de siempre, para no romper la config de Railway.
        return cls._segundos_de_entorno("MARKET_DATA_CACHE_SEGUNDOS", cls._VIGENCIA_SEGUNDOS_DEFECTO)

    @classmethod
    def _reintento_segundos(cls):
        return cls._segundos_de_entorno("MARKET_DATA_REINTENTO_SEGUNDOS", cls._REINTENTO_SEGUNDOS_DEFECTO)

    @staticmethod
    def _ahora():
        # UTC "ingenuo" (sin tzinfo), como se guardan las fechas en MySQL.
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _cotizacion_externa(ticker: str):
        api_key = os.environ.get("MARKET_DATA_API_KEY")
        if not api_key:
            return None

        parametros = urlencode(
            {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": api_key}
        )
        solicitud = Request(
            f"https://www.alphavantage.co/query?{parametros}",
            headers={"Accept": "application/json", "User-Agent": "InverTec/1.0"},
        )
        try:
            with urlopen(solicitud, timeout=5) as respuesta:
                datos = json.load(respuesta)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return None

        cotizacion = datos.get("Global Quote", {})
        precio = cotizacion.get("05. price")
        cambio_porcentaje = cotizacion.get("10. change percent", "").rstrip("%")
        try:
            precio_decimal = Decimal(str(precio)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            return None
        try:
            cambio_decimal = Decimal(str(cambio_porcentaje)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            cambio_decimal = None
        return {"precio": str(precio_decimal), "cambio_porcentaje": str(cambio_decimal) if cambio_decimal is not None else None}

    @staticmethod
    def _cambio_demo(ticker: str):
        # Cambio simulado pero estable por ticker (mismo valor en cada carga),
        # NO son datos de mercado reales. Solo se usa mientras no hay dato real.
        semilla = sum(ord(caracter) for caracter in ticker)
        return str(Decimal((semilla % 400) - 200) / Decimal("100"))

    # ---- Lectura (única vía por la que la app obtiene precios) -------------

    @staticmethod
    def _columnas_cotizacion():
        return (
            Cotizacion.ticker,
            Cotizacion.precio,
            Cotizacion.cambio_porcentaje,
            Cotizacion.actualizado_en,
            Cotizacion.ultimo_intento_en,
        )

    @classmethod
    def _leer_filas(cls):
        # Se devuelven filas planas (no objetos ORM), así un commit posterior no
        # las "expira" ni obliga a volver a consultar la base.
        filas = db.session.execute(select(*cls._columnas_cotizacion())).all()
        return {fila.ticker: fila for fila in filas}

    @classmethod
    def _leer_fila(cls, ticker: str):
        return db.session.execute(
            select(*cls._columnas_cotizacion()).where(Cotizacion.ticker == ticker)
        ).first()

    @classmethod
    def _fila_a_cotizacion(cls, ticker: str, fila):
        if fila is None:
            # Fila ausente (p. ej. BD sin sembrar): se usa la referencia simulada.
            return {
                "precio": PRECIOS_BASE[ticker],
                "cambio_porcentaje": cls._cambio_demo(ticker),
                "real": False,
                "cambio_real": False,
                "actualizado_en": None,
            }
        real = fila.actualizado_en is not None
        cambio_real = real and fila.cambio_porcentaje is not None
        return {
            "precio": str(Decimal(fila.precio).quantize(Decimal("0.01"))),
            "cambio_porcentaje": (
                str(Decimal(fila.cambio_porcentaje).quantize(Decimal("0.01")))
                if fila.cambio_porcentaje is not None
                else cls._cambio_demo(ticker)
            ),
            "real": real,
            "cambio_real": cambio_real,
            "actualizado_en": fila.actualizado_en,
        }

    @classmethod
    def _cotizacion(cls, ticker: str):
        return cls._fila_a_cotizacion(ticker, cls._leer_fila(ticker))

    @classmethod
    def _precio_actual(cls, ticker: str):
        return cls._cotizacion(ticker)["precio"]

    @classmethod
    def ultima_actualizacion(cls):
        """Fecha (UTC) del dato real más reciente, o None si aún no hay ninguno."""
        return db.session.scalar(select(func.max(Cotizacion.actualizado_en)))

    @staticmethod
    def _iso_utc(momento):
        return momento.isoformat() + "Z" if momento is not None else None

    # ---- Refresco (única vía por la que se llama a Alpha Vantage) ----------

    @classmethod
    def _esta_vencida(cls, fila, limite_vigencia):
        return fila is None or fila.actualizado_en is None or fila.actualizado_en < limite_vigencia

    @classmethod
    def _descargar_y_guardar(cls, tickers, pausa=None):

        pausa = cls._PAUSA_ENTRE_PETICIONES if pausa is None else pausa
        actualizadas, fallidas, sin_intentar = [], [], []
        for indice, ticker in enumerate(tickers):
            if indice:
                time.sleep(pausa)
            cotizacion = cls._cotizacion_externa(ticker)
            if cotizacion is None:
                fallidas.append(ticker)
                sin_intentar = list(tickers[indice + 1:])
                break
            fila = db.session.get(Cotizacion, ticker)
            if fila is None:
                fila = Cotizacion(ticker=ticker)
                db.session.add(fila)
            ahora = cls._ahora()
            fila.precio = Decimal(cotizacion["precio"])
            fila.cambio_porcentaje = (
                Decimal(cotizacion["cambio_porcentaje"])
                if cotizacion["cambio_porcentaje"] is not None
                else None
            )
            fila.actualizado_en = ahora
            fila.ultimo_intento_en = ahora
            db.session.commit()
            actualizadas.append(ticker)
        return {"actualizadas": actualizadas, "fallidas": fallidas, "sin_intentar": sin_intentar}

    @classmethod
    def refrescar_cotizaciones(cls, forzar=False, pausa=None):

        filas = cls._leer_filas()
        limite = cls._ahora() - timedelta(seconds=cls._vigencia_segundos())
        tickers = [
            ticker for ticker in sorted(CATALOGO)
            if forzar or cls._esta_vencida(filas.get(ticker), limite)
        ]
        return cls._descargar_y_guardar(tickers, pausa)

    @classmethod
    def refrescar_manual(cls):

        if not os.environ.get("MARKET_DATA_API_KEY"):
            return None, "MARKET_DATA_API_KEY no está configurada."

        ultima = cls.ultima_actualizacion()
        if ultima is not None:
            transcurridos = (cls._ahora() - ultima).total_seconds()
            faltan = cls._ENFRIAMIENTO_MANUAL_SEGUNDOS - transcurridos
            if faltan > 0:
                return None, f"Espera {int(faltan) + 1}s antes de volver a actualizar."

        return cls.refrescar_cotizaciones(forzar=True), None

        ahora = cls._ahora()
        limite_vigencia = ahora - timedelta(seconds=cls._vigencia_segundos())
        limite_reintento = ahora - timedelta(seconds=cls._reintento_segundos())
        ganadas = []
        for ticker, fila in sorted(filas.items()):
            toca_reintentar = fila.ultimo_intento_en is None or fila.ultimo_intento_en < limite_reintento
            if not (cls._esta_vencida(fila, limite_vigencia) and toca_reintentar):
                continue
            resultado = db.session.execute(
                update(Cotizacion)
                .where(Cotizacion.ticker == ticker)
                .where(or_(Cotizacion.actualizado_en.is_(None), Cotizacion.actualizado_en < limite_vigencia))
                .where(or_(Cotizacion.ultimo_intento_en.is_(None), Cotizacion.ultimo_intento_en < limite_reintento))
                .values(ultimo_intento_en=ahora)
            )
            db.session.commit()
            if resultado.rowcount == 1:
                ganadas.append(ticker)
        return ganadas

    @classmethod
    def _refrescar_en_segundo_plano(cls, tickers):
        app = current_app._get_current_object()

        def tarea():
            with app.app_context():
                try:
                    resumen = cls._descargar_y_guardar(tickers)
                    app.logger.info("Refresco de cotizaciones: %s", resumen)
                except Exception:
                    app.logger.exception("Falló el refresco de cotizaciones")
                finally:
                    db.session.remove()

        threading.Thread(target=tarea, name="refresco-cotizaciones", daemon=True).start()

    @classmethod
    def _programar_refresco(cls, filas):
        # Sin API key (desarrollo local) o en pruebas no hay nada que refrescar.
        if not os.environ.get("MARKET_DATA_API_KEY") or current_app.config.get("TESTING"):
            return
        ganadas = cls._reclamar_vencidas(filas)
        if ganadas:
            cls._refrescar_en_segundo_plano(ganadas)

    # ---- Consultas públicas ------------------------------------------------

    @classmethod
    def listar_catalogo(cls):
        filas = cls._leer_filas()
        resultado = []
        for ticker, datos in sorted(CATALOGO.items()):
            cotizacion = cls._fila_a_cotizacion(ticker, filas.get(ticker))
            resultado.append(
                {
                    "ticker": ticker,
                    "nombre_empresa": datos["nombre_empresa"],
                    "precio_actual": cotizacion["precio"],
                    "cambio_porcentaje": cotizacion["cambio_porcentaje"],
                    "cambio_real": cotizacion["cambio_real"],
                    "precio_real": cotizacion["real"],
                    "actualizado_en": cls._iso_utc(cotizacion["actualizado_en"]),
                }
            )
        # Después de armar la respuesta: el refresco corre aparte y no retrasa la página.
        cls._programar_refresco(filas)
        return resultado

    @classmethod
    def obtener_por_ticker(cls, ticker: str):
        clave = (ticker or "").strip().upper()
        if clave not in CATALOGO:
            return None
        volatilidad = Decimal(CATALOGO[clave]["volatilidad"]) * Decimal("100")
        cotizacion = cls._cotizacion(clave)
        return {
            "ticker": clave,
            "nombre_empresa": CATALOGO[clave]["nombre_empresa"],
            "precio_actual": cotizacion["precio"],
            "cambio_porcentaje": cotizacion["cambio_porcentaje"],
            "cambio_real": cotizacion["cambio_real"],
            "precio_real": cotizacion["real"],
            "actualizado_en": cls._iso_utc(cotizacion["actualizado_en"]),
            "volatilidad": str(volatilidad.quantize(Decimal("0.01"))),
        }

    @classmethod
    def calcular_riesgo(cls, ticker: str, cantidad, saldo_virtual):
        clave = (ticker or "").strip().upper()
        if clave not in CATALOGO:
            raise ErrorNegocio("La acción no existe", 404)

        try:
            cantidad_decimal = Decimal(str(cantidad))
            saldo_decimal = Decimal(str(saldo_virtual))
        except (InvalidOperation, TypeError, ValueError):
            raise ErrorNegocio("La cantidad o el saldo no son válidos")

        precio_decimal = Decimal(cls._precio_actual(clave))

        if cantidad_decimal <= 0 or precio_decimal <= 0:
            raise ErrorNegocio("La cantidad y el precio deben ser mayores a cero")
        if saldo_decimal <= 0:
            raise ErrorNegocio("El saldo virtual no puede ser cero")

        valor_total = cantidad_decimal * precio_decimal
        exposicion = (valor_total / saldo_decimal) * Decimal("100")
        volatilidad = Decimal(CATALOGO[clave]["volatilidad"])
        riesgo = (exposicion * Decimal("0.60")) + (volatilidad * Decimal("100"))
        riesgo = min(max(riesgo, Decimal("0")), Decimal("100"))

        if riesgo < Decimal("25"):
            riesgo_nivel = "bajo"
        elif riesgo < Decimal("40"):
            riesgo_nivel = "medio"
        else:
            riesgo_nivel = "alto"

        return {
            "ticker": clave,
            "nombre_empresa": CATALOGO[clave]["nombre_empresa"],
            "cantidad": str(cantidad_decimal),
            "precio_unitario": str(precio_decimal),
            "valor_total": str(valor_total),
            "saldo_virtual": str(saldo_decimal),
            "exposicion_porcentaje": str(exposicion.quantize(Decimal("0.01"))),
            "volatilidad_porcentaje": str(
                (volatilidad * Decimal("100")).quantize(Decimal("0.01"))
            ),
            "riesgo_calculado": str(riesgo.quantize(Decimal("0.01"))),
            "riesgo_nivel": riesgo_nivel,
        }