from pathlib import Path

from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

RAIZ = Path(__file__).resolve().parent.parent

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
