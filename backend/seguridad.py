from flask import jsonify
from flask_jwt_extended import get_jwt, jwt_required
from functools import wraps

from backend.conexion import jwt
from backend.repositorios.usuario import UsuarioRepo


def json_error(mensaje: str, codigo: int):
    return jsonify({"error": mensaje}), codigo


@jwt.user_lookup_loader
def cargar_usuario(_tipo, datos):
    return UsuarioRepo().por_id(int(datos["sub"]))


@jwt.unauthorized_loader
def sin_token(_motivo):
    return json_error("Token requerido", 401)


@jwt.invalid_token_loader
def token_invalido(_motivo):
    return json_error("Token inválido", 401)


@jwt.expired_token_loader
def token_expirado(_encabezado, _datos):
    return json_error("Token expirado", 401)


@jwt.needs_fresh_token_loader
def token_no_fresco(_encabezado, _datos):
    return json_error("Token requerido", 401)


def rol_admin(fn):
    @wraps(fn)
    @jwt_required()
    def envoltura(*args, **kwargs):
        if get_jwt().get("rol") != "administrador":
            return json_error("No autorizado", 403)
        return fn(*args, **kwargs)

    return envoltura
