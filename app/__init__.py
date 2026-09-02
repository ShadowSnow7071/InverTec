import os

from flask import Flask

from app.config import config_by_name
from app.extensions import db, migrate


def create_app(config_name=None):
    app = Flask(__name__)
    name = config_name or os.environ.get("APP_CONFIG", "development")
    app.config.from_object(config_by_name[name])

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401
    from app.views import bp as main_bp

    app.register_blueprint(main_bp)
    return app
