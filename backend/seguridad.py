from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from functools import wraps

from backend.conexion import db, jwt
from backend.modelos import Usuario


def json_error(mensaje: str, codigo: int):
    return jsonify({"error": mensaje}), codigo


@jwt.user_lookup_loader
def cargar_usuario(_jwt_header, jwt_data):
    return db.session.get(Usuario, int(jwt_data["sub"]))


@jwt.unauthorized_loader
def sin_token(_motivo):
    return json_error("Token requerido", 401)


@jwt.invalid_token_loader
def token_invalido(_motivo):
    return json_error("Token inválido", 401)


@jwt.expired_token_loader
def token_expirado(_encabezado, _datos):
    return json_error("Token expirado", 401)


def usuario_actual():
    return db.session.get(Usuario, int(get_jwt_identity()))


def rol_admin(fn):
    @wraps(fn)
    @jwt_required()
    def envoltura(*args, **kwargs):
        if get_jwt().get("rol") != "administrador":
            return json_error("No autorizado", 403)
        return fn(*args, **kwargs)

    return envoltura