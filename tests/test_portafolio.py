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


def test_portafolio_requiere_autenticacion(client):
    respuesta = client.get("/api/portafolio")

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Token requerido"}