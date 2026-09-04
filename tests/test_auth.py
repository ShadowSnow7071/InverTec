import pytest
from werkzeug.security import generate_password_hash

from backend.config import Config, TestingConfig
from backend.conexion import db
from backend.modelos import Portafolio, RolUsuario, Usuario


def _registrar(client, correo="ana@example.com"):
    return client.post(
        "/api/auth/registro",
        json={
            "nombre": "Ana",
            "correo": correo,
            "password": "secreto12",
        },
    )


def test_paginas_login_y_registro(client):
    assert client.get("/login").status_code == 200
    assert client.get("/registro").status_code == 200


def test_registro_api_crea_usuario_y_portafolio(client, app):
    respuesta = _registrar(client)
    assert respuesta.status_code == 201
    cuerpo = respuesta.get_json()
    assert "access_token" in cuerpo
    assert "refresh_token" in cuerpo
    assert cuerpo["usuario"]["correo"] == "ana@example.com"
    assert cuerpo["usuario"]["rol"] == "inversionista"
    with app.app_context():
        assert db.session.query(Portafolio).count() == 1


def test_registro_correo_duplicado(client):
    _registrar(client)
    respuesta = _registrar(client)
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "El correo ya está registrado"


def test_login_invalido(client):
    respuesta = client.post(
        "/api/auth/login",
        json={"correo": "nadie@example.com", "password": "secreto12"},
    )
    assert respuesta.status_code == 401


def test_login_me_y_patch(client):
    _registrar(client)
    login = client.post(
        "/api/auth/login",
        json={"correo": "ana@example.com", "password": "secreto12"},
    )
    token = login.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/usuarios/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["nombre"] == "Ana"

    actualizado = client.patch(
        "/api/usuarios/me",
        headers=headers,
        json={"nombre": "Ana López"},
    )
    assert actualizado.status_code == 200
    assert actualizado.get_json()["nombre"] == "Ana López"


def test_me_sin_token(client):
    respuesta = client.get("/api/usuarios/me")
    assert respuesta.status_code == 401


def test_refresh(client):
    registro = _registrar(client)
    refresh = registro.get_json()["refresh_token"]
    respuesta = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert respuesta.status_code == 200
    assert "access_token" in respuesta.get_json()


def test_listar_usuarios_solo_admin(client, app):
    _registrar(client)
    login = client.post(
        "/api/auth/login",
        json={"correo": "ana@example.com", "password": "secreto12"},
    )
    token_inv = login.get_json()["access_token"]
    prohibido = client.get(
        "/api/usuarios",
        headers={"Authorization": f"Bearer {token_inv}"},
    )
    assert prohibido.status_code == 403

    with app.app_context():
        admin = Usuario(
            nombre="Admin",
            correo="admin@example.com",
            password_hash=generate_password_hash("secreto12"),
            rol=RolUsuario.administrador,
        )
        db.session.add(admin)
        db.session.commit()

    admin_login = client.post(
        "/api/auth/login",
        json={"correo": "admin@example.com", "password": "secreto12"},
    )
    token_admin = admin_login.get_json()["access_token"]
    lista = client.get(
        "/api/usuarios",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert lista.status_code == 200
    correos = {u["correo"] for u in lista.get_json()}
    assert "ana@example.com" in correos
    assert "admin@example.com" in correos


def test_login_html_credenciales_invalidas(client):
    respuesta = client.post(
        "/login",
        data={"correo": "nadie@example.com", "password": "secreto12"},
    )
    assert respuesta.status_code == 401


def test_registro_password_corta(client):
    respuesta = client.post(
        "/api/auth/registro",
        json={"nombre": "Ana", "correo": "ana@example.com", "password": "corta"},
    )
    assert respuesta.status_code == 400


def test_config_requiere_secretos_validos_fuera_de_testing(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setattr(Config, "SECRET_KEY", None, raising=False)
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", None, raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY|JWT_SECRET_KEY"):
        Config.validate()

    monkeypatch.setattr(Config, "SECRET_KEY", "cambiar-en-desarrollo", raising=False)
    monkeypatch.setattr(
        Config,
        "JWT_SECRET_KEY",
        "cambiar-jwt-en-desarrollo-min-32-bytes",
        raising=False,
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY|JWT_SECRET_KEY"):
        Config.validate()

    monkeypatch.setattr(Config, "SECRET_KEY", "a" * 32, raising=False)
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", "b" * 32, raising=False)
    Config.validate()
    TestingConfig.validate()


def test_registro_html_redirige_a_perfil(client):
    respuesta = client.post(
        "/registro",
        data={
            "nombre": "Luis",
            "correo": "luis@example.com",
            "password": "secreto12",
        },
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert b"Luis" in respuesta.data
    assert b"luis@example.com" in respuesta.data
