from backend.conexion import db
from backend.modelos import Portafolio, Usuario


def datos_registro(correo="ana@example.com"):
    return {
        "nombre": "Ana",
        "correo": correo,
        "password": "secreto12",
    }


def test_registro_crea_usuario_portafolio_y_tokens(client, app):
    respuesta = client.post("/api/auth/registro", json=datos_registro())

    assert respuesta.status_code == 201
    cuerpo = respuesta.get_json()
    assert cuerpo["usuario"]["correo"] == "ana@example.com"
    assert "access_token" in cuerpo
    assert "refresh_token" in cuerpo

    with app.app_context():
        usuario = db.session.query(Usuario).one()
        assert usuario.portafolio is not None
        assert usuario.portafolio.saldo_virtual == 10000
        assert usuario.password_hash != "secreto12"


def test_registro_rechaza_correo_duplicado(client):
    client.post("/api/auth/registro", json=datos_registro())
    respuesta = client.post("/api/auth/registro", json=datos_registro())

    assert respuesta.status_code == 400
    assert respuesta.get_json() == {"error": "El correo ya está registrado"}


def test_login_y_perfil_protegido(client):
    client.post("/api/auth/registro", json=datos_registro())
    login = client.post(
        "/api/auth/login",
        json={"correo": "ANA@example.com", "password": "secreto12"},
    )
    token = login.get_json()["access_token"]

    respuesta = client.get(
        "/api/usuarios/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert login.status_code == 200
    assert respuesta.status_code == 200
    assert respuesta.get_json()["saldo_virtual"] == "10000.00"


def test_perfil_sin_token_rechaza_acceso(client):
    respuesta = client.get("/api/usuarios/me")

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Token requerido"}


def test_login_rechaza_credenciales_invalidas(client):
    respuesta = client.post(
        "/api/auth/login",
        json={"correo": "nadie@example.com", "password": "secreto12"},
    )

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Correo o contraseña incorrectos"}


def test_refresh_emite_nuevo_access_token(client):
    registro = client.post("/api/auth/registro", json=datos_registro())
    refresh_token = registro.get_json()["refresh_token"]

    respuesta = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert respuesta.status_code == 200
    assert "access_token" in respuesta.get_json()


def test_flujo_html_registro_perfil_y_logout(client):
    registro = client.post(
        "/registro",
        data={
            "nombre": "Luis",
            "correo": "luis@example.com",
            "password": "secreto12",
        },
        follow_redirects=True,
    )

    assert registro.status_code == 200
    assert b"Hola, Luis" in registro.data
    assert b"10000.00" in registro.data

    logout = client.post("/logout", follow_redirects=True)

    assert logout.status_code == 200
    assert b"Comenzar" in logout.data