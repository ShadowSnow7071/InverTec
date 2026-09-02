from decimal import Decimal

from backend.conexion import db
from backend.modelos import (
    Accion,
    Movimiento,
    Portafolio,
    RolUsuario,
    TipoMovimiento,
    Usuario,
)


def test_usuario_y_portafolio_uno_a_uno(app):
    usuario = Usuario(
        nombre="Ana",
        correo="ana@example.com",
        password_hash="hash",
        rol=RolUsuario.inversionista,
    )
    db.session.add(usuario)
    db.session.flush()

    portafolio = Portafolio(usuario_id=usuario.id)
    db.session.add(portafolio)
    db.session.commit()

    guardado = db.session.get(Usuario, usuario.id)
    assert guardado.portafolio is not None
    assert guardado.portafolio.saldo_virtual == Decimal("10000.00")


def test_movimiento_relaciona_portafolio_y_accion(app):
    usuario = Usuario(
        nombre="Luis",
        correo="luis@example.com",
        password_hash="hash",
    )
    db.session.add(usuario)
    db.session.flush()

    portafolio = Portafolio(usuario_id=usuario.id)
    accion = Accion(ticker="GOOGL", nombre_empresa="Alphabet")
    db.session.add_all([portafolio, accion])
    db.session.flush()

    movimiento = Movimiento(
        portafolio_id=portafolio.id,
        accion_id=accion.id,
        tipo=TipoMovimiento.compra,
        cantidad=Decimal("2.5000"),
        precio_unitario=Decimal("150.00"),
        riesgo_calculado=Decimal("12.50"),
    )
    db.session.add(movimiento)
    db.session.commit()

    guardado = db.session.get(Movimiento, movimiento.id)
    assert guardado.portafolio.id == portafolio.id
    assert guardado.accion.ticker == "GOOGL"
    assert guardado.tipo == TipoMovimiento.compra
