import pytest

from backend import create_app
from backend.conexion import db
from backend.servicios.auth import AuthServicio


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    yield app.test_client()
    # Limpiar contadores de rate limiting después de cada test
    AuthServicio._intentos_login.clear()
    AuthServicio._intentos_login_ip.clear()
