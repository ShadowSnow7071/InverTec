from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from backend.seguridad import json_error, rol_admin
from backend.servicios.auth import ErrorNegocio
from backend.servicios.usuario import UsuarioServicio

bp = Blueprint("api_usuarios", __name__)
servicio = UsuarioServicio()


@bp.get("/api/usuarios/me")
@jwt_required()
def me():
    if current_user is None:
        return json_error("Token inválido", 401)
    return jsonify(servicio.perfil(current_user))


@bp.patch("/api/usuarios/me")
@jwt_required()
def actualizar_me():
    if current_user is None:
        return json_error("Token inválido", 401)
    datos = request.get_json(silent=True) or {}
    try:
        return jsonify(servicio.actualizar_perfil(current_user, datos))
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)


@bp.get("/api/usuarios")
@rol_admin
def listar():
    return jsonify(servicio.listar())
