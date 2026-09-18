from decimal import Decimal

from backend.conexion import db
from backend.modelos import Accion, Movimiento, Portafolio, TipoMovimiento, Usuario


def registrar_y_obtener_token(client, correo):
    respuesta = client.post(
        "/api/auth/registro",
        json={
            "nombre": correo.split("@")[0],
            "correo": correo,
            "password": "secreto12",
        },
    )
    return respuesta.get_json()["access_token"]


def test_portafolio_devuelve_saldo_y_posiciones(client, app):
    token = registrar_y_obtener_token(client, "ana@example.com")
    with app.app_context():
        usuario = db.session.query(Usuario).one()
        accion = Accion(ticker="GOOGL", nombre_empresa="Alphabet")
        db.session.add(accion)
        db.session.flush()
        db.session.add_all(
            [
                Movimiento(
                    portafolio_id=usuario.portafolio.id,
                    accion_id=accion.id,
                    tipo=TipoMovimiento.compra,
                    cantidad=Decimal("5.0000"),
                    precio_unitario=Decimal("150.00"),
                ),
                Movimiento(
                    portafolio_id=usuario.portafolio.id,
                    accion_id=accion.id,
                    tipo=TipoMovimiento.venta,
                    cantidad=Decimal("1.5000"),
                    precio_unitario=Decimal("155.00"),
                ),
            ]
        )
        db.session.commit()

    respuesta = client.get(
        "/api/portafolio",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["saldo_virtual"] == "10000.00"
    assert cuerpo["posiciones"] == [
        {
            "accion_id": 1,
            "ticker": "GOOGL",
            "nombre_empresa": "Alphabet",
            "cantidad": "3.5000",
        }
    ]


def test_movimientos_devuelve_historial_del_usuario(client, app):
    token = registrar_y_obtener_token(client, "luis@example.com")
    with app.app_context():
        usuario = db.session.query(Usuario).one()
        accion = Accion(ticker="NVDA", nombre_empresa="NVIDIA")
        db.session.add(accion)
        db.session.flush()
        db.session.add(
            Movimiento(
                portafolio_id=usuario.portafolio.id,
                accion_id=accion.id,
                tipo=TipoMovimiento.compra,
                cantidad=Decimal("2.0000"),
                precio_unitario=Decimal("120.00"),
                riesgo_calculado=Decimal("25.00"),
            )
        )
        db.session.commit()

    respuesta = client.get(
        "/api/portafolio/movimientos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()[0]["ticker"] == "NVDA"
    assert respuesta.get_json()[0]["riesgo_calculado"] == "25.00"
    assert respuesta.get_json()[0]["riesgo_nivel"] == "bajo"


def test_compra_actualiza_saldo_y_movimiento(client, app, monkeypatch):
    monkeypatch.setattr("backend.servicios.acciones.AccionServicio._precio_externo", lambda _: None)
    token = registrar_y_obtener_token(client, "compra@example.com")

    respuesta = client.post(
        "/api/portafolio/comprar",
        headers={"Authorization": f"Bearer {token}"},
        json={"ticker": "AAPL", "cantidad": "2", "riesgo_calculado": "22.57"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["saldo_virtual"] == "9571.60"
    assert cuerpo["posiciones"][0]["ticker"] == "AAPL"
    assert cuerpo["posiciones"][0]["cantidad"] == "2.0000"
    assert cuerpo["movimientos"][0]["tipo"] == "compra"


def test_venta_actualiza_saldo_y_movimiento(client, app, monkeypatch):
    monkeypatch.setattr("backend.servicios.acciones.AccionServicio._precio_externo", lambda _: None)
    token = registrar_y_obtener_token(client, "venta@example.com")
    with app.app_context():
        usuario = db.session.query(Usuario).one()
        accion = Accion(ticker="MSFT", nombre_empresa="Microsoft")
        db.session.add(accion)
        db.session.flush()
        db.session.add(
            Movimiento(
                portafolio_id=usuario.portafolio.id,
                accion_id=accion.id,
                tipo=TipoMovimiento.compra,
                cantidad=Decimal("3.0000"),
                precio_unitario=Decimal("214.20"),
            )
        )
        db.session.commit()

    respuesta = client.post(
        "/api/portafolio/vender",
        headers={"Authorization": f"Bearer {token}"},
        json={"ticker": "MSFT", "cantidad": "1.5000", "riesgo_calculado": "21.84"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["saldo_virtual"] == "10640.12"
    assert cuerpo["posiciones"][0]["cantidad"] == "1.5000"
    assert cuerpo["movimientos"][0]["tipo"] == "venta"


def test_compra_guarda_riesgo_calculado_si_viene_en_payload(client, app, monkeypatch):
    monkeypatch.setattr("backend.servicios.acciones.AccionServicio._precio_externo", lambda _: None)
    token = registrar_y_obtener_token(client, "riesgo_compra@example.com")

    respuesta = client.post(
        "/api/portafolio/comprar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "ticker": "AAPL",
            "cantidad": "2",
            "riesgo_calculado": "22.57",
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["movimientos"][0]["riesgo_calculado"] == "22.57"


def test_compra_requiere_riesgo_calculado(client, monkeypatch):
    monkeypatch.setattr("backend.servicios.acciones.AccionServicio._precio_externo", lambda _: None)
    token = registrar_y_obtener_token(client, "riesgo_requerido@example.com")

    respuesta = client.post(
        "/api/portafolio/comprar",
        headers={"Authorization": f"Bearer {token}"},
        json={"ticker": "AAPL", "cantidad": "2"},
    )

    assert respuesta.status_code == 400
    assert "consultar el riesgo" in respuesta.get_json()["error"]


def test_api_acciones_devuelve_catalogo_publico(client):
    respuesta = client.get("/api/acciones")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert any(item["ticker"] == "AAPL" for item in cuerpo)
    assert all("precio_actual" in item for item in cuerpo)


def test_api_accion_devuelve_precio_demo_sin_api_key(client, monkeypatch):
    monkeypatch.delenv("MARKET_DATA_API_KEY", raising=False)

    respuesta = client.get("/api/acciones/NVDA/precio")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "ticker": "NVDA",
        "nombre_empresa": "NVIDIA",
        "precio_actual": "127.85",
    }


def test_api_accion_incluye_volatilidad_y_detalle(client, monkeypatch):
    monkeypatch.delenv("MARKET_DATA_API_KEY", raising=False)

    respuesta = client.get("/api/acciones/AAPL")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["ticker"] == "AAPL"
    assert cuerpo["nombre_empresa"] == "Apple Inc."
    assert cuerpo["volatilidad"] == "20.00"
    assert cuerpo["precio_actual"] == "214.20"


def test_riesgo_movimiento_retorna_escala_valida(client, app, monkeypatch):
    monkeypatch.setattr("backend.servicios.acciones.AccionServicio._precio_externo", lambda _: None)
    token = registrar_y_obtener_token(client, "riesgo@example.com")

    respuesta = client.post(
        "/api/portafolio/movimientos/riesgo",
        headers={"Authorization": f"Bearer {token}"},
        json={"ticker": "AAPL", "cantidad": "2", "precio_unitario": "0.01"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["ticker"] == "AAPL"
    assert 0 <= float(cuerpo["riesgo_calculado"]) <= 100
    assert float(cuerpo["exposicion_porcentaje"]) > 0
    assert cuerpo["volatilidad_porcentaje"] == "20.00"
    assert cuerpo["riesgo_nivel"] in {"bajo", "medio", "alto"}

def test_analisis_portafolio_devuelve_estadisticas(client, app, monkeypatch):
    monkeypatch.setattr("backend.servicios.acciones.AccionServicio._precio_externo", lambda _: None)
    token = registrar_y_obtener_token(client, "analisis@example.com")
    with app.app_context():
        usuario = db.session.query(Usuario).one()
        accion_aapl = Accion(ticker="AAPL", nombre_empresa="Apple Inc.")
        accion_googl = Accion(ticker="GOOGL", nombre_empresa="Alphabet")
        db.session.add_all([accion_aapl, accion_googl])
        db.session.flush()
        db.session.add_all(
            [
                Movimiento(
                    portafolio_id=usuario.portafolio.id,
                    accion_id=accion_aapl.id,
                    tipo=TipoMovimiento.compra,
                    cantidad=Decimal("2.0000"),
                    precio_unitario=Decimal("214.20"),
                ),
                Movimiento(
                    portafolio_id=usuario.portafolio.id,
                    accion_id=accion_googl.id,
                    tipo=TipoMovimiento.compra,
                    cantidad=Decimal("1.0000"),
                    precio_unitario=Decimal("170.00"),
                ),
            ]
        )
        db.session.commit()

    respuesta = client.get(
        "/api/portafolio/analisis",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert "saldo_disponible" in cuerpo
    assert "valor_total_posiciones" in cuerpo
    assert "distribucion_activos" in cuerpo
    assert "cantidad_compras" in cuerpo
    assert "cantidad_ventas" in cuerpo
    assert "volatilidades" in cuerpo
    assert "posiciones_count" in cuerpo
    assert cuerpo["cantidad_compras"] == 2
    assert cuerpo["cantidad_ventas"] == 0
    assert cuerpo["posiciones_count"] == 2
    assert "AAPL" in cuerpo["distribucion_activos"]
    assert "GOOGL" in cuerpo["distribucion_activos"]

def test_api_detalle_movimiento_devuelve_un_movimiento(client, app):
    token = registrar_y_obtener_token(client, "detalle_mov@example.com")
    with app.app_context():
        usuario = db.session.query(Usuario).one()
        accion = Accion(ticker="MSFT", nombre_empresa="Microsoft")
        db.session.add(accion)
        db.session.flush()
        movimiento = Movimiento(
            portafolio_id=usuario.portafolio.id,
            accion_id=accion.id,
            tipo=TipoMovimiento.compra,
            cantidad=Decimal("1.5000"),
            precio_unitario=Decimal("200.00"),
            riesgo_calculado=Decimal("42.50"),
        )
        db.session.add(movimiento)
        db.session.commit()
        movimiento_id = movimiento.id

    respuesta = client.get(
        f"/api/portafolio/movimientos/{movimiento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["id"] == movimiento_id
    assert cuerpo["ticker"] == "MSFT"
    assert cuerpo["riesgo_calculado"] == "42.50"
    assert cuerpo["riesgo_nivel"] == "medio"


def test_api_usuarios_listado_requiere_rol_administrador(client, app):
    token = registrar_y_obtener_token(client, "admin@example.com")
    with app.app_context():
        usuario = db.session.query(Usuario).one()
        usuario.rol = "administrador"
        db.session.commit()

    respuesta = client.get(
        "/api/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert isinstance(cuerpo, list)
    assert any(item["correo"] == "admin@example.com" for item in cuerpo)


def test_detalle_movimiento_inexistente_devuelve_404(client):
    token = registrar_y_obtener_token(client, "detalle_inexistente@example.com")

    respuesta = client.get(
        "/api/portafolio/movimientos/9999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 404
    assert respuesta.get_json() == {"error": "Movimiento no encontrado"}


def test_portafolio_requiere_autenticacion(client):
    respuesta = client.get("/api/portafolio")

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Token requerido"}