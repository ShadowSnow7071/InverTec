import os

from backend import create_app
from backend.conexion import db


app = create_app(os.environ.get("RUN_CONFIG", "testing"))

if app.config.get("TESTING"):
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    app.run()