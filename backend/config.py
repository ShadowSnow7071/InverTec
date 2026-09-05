import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True
    JWT_CSRF_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    _PLACEHOLDER_VALUES = {
        "dev-secret-key",
        "dev-jwt-secret-key-min-32-bytes",
        "cambiar-en-desarrollo",
        "cambiar-jwt-en-desarrollo-min-32-bytes",
        "change-me",
        "secret",
        "jwt-secret",
        "placeholder",
        "example",
    }

    @classmethod
    def validate(cls):
        if getattr(cls, "TESTING", False):
            return

        secret_key = os.environ.get("SECRET_KEY") or cls.SECRET_KEY
        jwt_secret_key = os.environ.get("JWT_SECRET_KEY") or cls.JWT_SECRET_KEY

        issues = []
        for nombre, valor in {"SECRET_KEY": secret_key, "JWT_SECRET_KEY": jwt_secret_key}.items():
            if not valor:
                issues.append(nombre)
                continue
            if valor in cls._PLACEHOLDER_VALUES or len(valor) < 32:
                issues.append(nombre)

        if secret_key and jwt_secret_key and secret_key == jwt_secret_key:
            issues.extend(["SECRET_KEY", "JWT_SECRET_KEY"])

        if issues:
            raise RuntimeError(
                "Configuración insegura: define SECRET_KEY y JWT_SECRET_KEY con valores únicos y de al menos 32 caracteres en el archivo .env."
            )


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-flask-secret-key-only-for-automated-tests"
    JWT_SECRET_KEY = "test-jwt-secret-key-only-for-automated-tests"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)

    @classmethod
    def validate(cls):
        return


class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "Strict"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
