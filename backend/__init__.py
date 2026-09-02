import os

from flask import Flask

from backend.config import config_by_name
from backend.conexion import RAIZ, db, migrate


def create_app(config_name=None):
    app = Flask(
        __name__,
        template_folder=str(RAIZ / "frontend" / "templates"),
        static_folder=str(RAIZ / "frontend" / "static"),
        instance_path=str(RAIZ / "instance"),
    )
    name = config_name or os.environ.get("APP_CONFIG", "development")
    app.config.from_object(config_by_name[name])

    db.init_app(app)
    migrate.init_app(app, db, directory=str(RAIZ / "database" / "migrations"))

    from backend import modelos  # noqa: F401
    from backend.rutas import bp as main_bp

    app.register_blueprint(main_bp)
    return app
