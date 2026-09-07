import os

from flask import Flask

from backend.config import config_by_name
from backend.conexion import RAIZ, db, jwt, migrate


def create_app(config_name=None):
    app = Flask(
        __name__,
        template_folder=str(RAIZ / "frontend" / "templates"),
        static_folder=str(RAIZ / "frontend" / "static"),
        instance_path=str(RAIZ / "instance"),
    )
    name = config_name or os.environ.get("APP_CONFIG", "development")
    config_cls = config_by_name[name]
    config_cls.validate()
    app.config.from_object(config_cls)

    db.init_app(app)
    migrate.init_app(app, db, directory=str(RAIZ / "database" / "migrations"))
    jwt.init_app(app)

    from backend import modelos  # noqa: F401
    from backend import seguridad  # noqa: F401
    from backend.api_auth import bp as api_auth_bp
    from backend.api_usuarios import bp as api_usuarios_bp
    from backend.rutas import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_usuarios_bp)

    from flask_jwt_extended import current_user, verify_jwt_in_request

    @app.context_processor
    def inyectar_usuario():
        try:
            verify_jwt_in_request(optional=True)
        except Exception:
            return {"usuario_actual": None}
        return {"usuario_actual": current_user}

    return app
