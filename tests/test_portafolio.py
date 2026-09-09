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


def test_compra_actualiza_saldo_y_movimiento(client, app):
    token = registrar_y_obtener_token(client, "compra@example.com")

    respuesta = client.post(
        "/api/portafolio/comprar",
        headers={"Authorization": f"Bearer {token}"},
        json={"ticker": "AAPL", "cantidad": "2", "precio_unitario": "150.00"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["saldo_virtual"] == "9700.00"
    assert cuerpo["posiciones"][0]["ticker"] == "AAPL"
    assert cuerpo["posiciones"][0]["cantidad"] == "2.0000"
    assert cuerpo["movimientos"][0]["tipo"] == "compra"


def test_venta_actualiza_saldo_y_movimiento(client, app):
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
                precio_unitario=Decimal("100.00"),
            )
        )
        db.session.commit()

    respuesta = client.post(
        "/api/portafolio/vender",
        headers={"Authorization": f"Bearer {token}"},
        json={"ticker": "MSFT", "cantidad": "1.5000", "precio_unitario": "110.00"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["saldo_virtual"] == "10165.00"
    assert cuerpo["posiciones"][0]["cantidad"] == "1.5000"
    assert cuerpo["movimientos"][0]["tipo"] == "venta"


def test_api_acciones_devuelve_catalogo_publico(client):
    respuesta = client.get("/api/acciones")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert any(item["ticker"] == "AAPL" for item in cuerpo)
    assert all("precio_actual" in item for item in cuerpo)


def test_riesgo_movimiento_retorna_escala_valida(client, app):
    token = registrar_y_obtener_token(client, "riesgo@example.com")

    respuesta = client.post(
        "/api/portafolio/movimientos/riesgo",
        headers={"Authorization": f"Bearer {token}"},
        json={"ticker": "AAPL", "cantidad": "2", "precio_unitario": "150.00"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["ticker"] == "AAPL"
    assert 0 <= float(cuerpo["riesgo_calculado"]) <= 100


def test_portafolio_requiere_autenticacion(client):
    respuesta = client.get("/api/portafolio")

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Token requerido"}