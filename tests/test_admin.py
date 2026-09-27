from decimal import Decimal

from backend.conexion import db
from backend.modelos import Accion, Movimiento, TipoMovimiento, Usuario


def registrar_y_obtener_token(client, correo):
    respuesta = client.post(
        "/api/auth/registro",
        json={
            "nombre": correo.split("@")[0],
            "correo": correo,
            "password": "Secreto12!",
        },
    )
    return respuesta.get_json()["access_token"]


def hacer_administrador(app, correo):
    with app.app_context():
        usuario = db.session.query(Usuario).filter_by(correo=correo).one()
        usuario.rol = "administrador"
        db.session.commit()


def test_estadisticas_requiere_rol_administrador(client):
    token = registrar_y_obtener_token(client, "normal@example.com")
    respuesta = client.get("/api/usuarios/estadisticas", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403


def test_estadisticas_devuelve_conteos_correctos(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    registrar_y_obtener_token(client, "usuario1@example.com")

    respuesta = client.get("/api/usuarios/estadisticas", headers={"Authorization": f"Bearer {token_admin}"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["usuarios_totales"] == 2
    assert cuerpo["usuarios_activos"] == 2
    assert cuerpo["operaciones_totales"] == 0
    assert Decimal(cuerpo["saldo_total"]) == Decimal("100000.00")


def test_bloquear_usuario_impide_login_posterior(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    registrar_y_obtener_token(client, "usuario1@example.com")
    with app.app_context():
        objetivo_id = db.session.query(Usuario).filter_by(correo="usuario1@example.com").one().id

    respuesta = client.patch(
        f"/api/usuarios/{objetivo_id}/estado",
        json={"activo": False},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.get_json()["activo"] is False

    login = client.post(
        "/api/auth/login",
        json={"correo": "usuario1@example.com", "password": "Secreto12!"},
    )
    assert login.status_code == 403
    assert "bloqueada" in login.get_json()["error"]


def test_desbloquear_usuario_permite_login_de_nuevo(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    registrar_y_obtener_token(client, "usuario1@example.com")
    with app.app_context():
        objetivo_id = db.session.query(Usuario).filter_by(correo="usuario1@example.com").one().id

    client.patch(
        f"/api/usuarios/{objetivo_id}/estado",
        json={"activo": False},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    respuesta = client.patch(
        f"/api/usuarios/{objetivo_id}/estado",
        json={"activo": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.get_json()["activo"] is True

    login = client.post(
        "/api/auth/login",
        json={"correo": "usuario1@example.com", "password": "Secreto12!"},
    )
    assert login.status_code == 200


def test_admin_no_puede_bloquear_su_propia_cuenta(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    with app.app_context():
        admin_id = db.session.query(Usuario).filter_by(correo="admin@example.com").one().id

    respuesta = client.patch(
        f"/api/usuarios/{admin_id}/estado",
        json={"activo": False},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 400
    assert "propia cuenta" in respuesta.get_json()["error"]


def test_cambiar_rol_actualiza_usuario(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    registrar_y_obtener_token(client, "usuario1@example.com")
    with app.app_context():
        objetivo_id = db.session.query(Usuario).filter_by(correo="usuario1@example.com").one().id

    respuesta = client.patch(
        f"/api/usuarios/{objetivo_id}/rol",
        json={"rol": "administrador"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.get_json()["rol"] == "administrador"


def test_cambiar_rol_invalido_devuelve_error(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    registrar_y_obtener_token(client, "usuario1@example.com")
    with app.app_context():
        objetivo_id = db.session.query(Usuario).filter_by(correo="usuario1@example.com").one().id

    respuesta = client.patch(
        f"/api/usuarios/{objetivo_id}/rol",
        json={"rol": "superadmin"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 400


def test_admin_no_puede_cambiar_su_propio_rol(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    with app.app_context():
        admin_id = db.session.query(Usuario).filter_by(correo="admin@example.com").one().id

    respuesta = client.patch(
        f"/api/usuarios/{admin_id}/rol",
        json={"rol": "inversionista"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 400


def test_eliminar_usuario_borra_portafolio_y_movimientos(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    registrar_y_obtener_token(client, "usuario1@example.com")
    with app.app_context():
        objetivo = db.session.query(Usuario).filter_by(correo="usuario1@example.com").one()
        objetivo_id = objetivo.id
        portafolio_id = objetivo.portafolio.id
        accion = Accion(ticker="AAPL", nombre_empresa="Apple")
        db.session.add(accion)
        db.session.flush()
        db.session.add(
            Movimiento(
                portafolio_id=portafolio_id,
                accion_id=accion.id,
                tipo=TipoMovimiento.compra,
                cantidad=Decimal("2.0000"),
                precio_unitario=Decimal("100.00"),
            )
        )
        db.session.commit()

    respuesta = client.delete(
        f"/api/usuarios/{objetivo_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 204

    with app.app_context():
        assert db.session.get(Usuario, objetivo_id) is None
        assert db.session.query(Movimiento).filter_by(portafolio_id=portafolio_id).count() == 0


def test_admin_no_puede_eliminar_su_propia_cuenta(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    with app.app_context():
        admin_id = db.session.query(Usuario).filter_by(correo="admin@example.com").one().id

    respuesta = client.delete(
        f"/api/usuarios/{admin_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert respuesta.status_code == 400


def test_auditoria_incluye_movimientos_de_todos_los_usuarios(client, app):
    token_admin = registrar_y_obtener_token(client, "admin@example.com")
    hacer_administrador(app, "admin@example.com")
    registrar_y_obtener_token(client, "usuario1@example.com")
    with app.app_context():
        objetivo = db.session.query(Usuario).filter_by(correo="usuario1@example.com").one()
        accion = Accion(ticker="MSFT", nombre_empresa="Microsoft")
        db.session.add(accion)
        db.session.flush()
        db.session.add(
            Movimiento(
                portafolio_id=objetivo.portafolio.id,
                accion_id=accion.id,
                tipo=TipoMovimiento.compra,
                cantidad=Decimal("3.0000"),
                precio_unitario=Decimal("200.00"),
            )
        )
        db.session.commit()

    respuesta = client.get("/api/usuarios/auditoria", headers={"Authorization": f"Bearer {token_admin}"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["usuario_correo"] == "usuario1@example.com"
    assert cuerpo[0]["ticker"] == "MSFT"


def test_auditoria_requiere_rol_administrador(client):
    token = registrar_y_obtener_token(client, "normal@example.com")
    respuesta = client.get("/api/usuarios/auditoria", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403
