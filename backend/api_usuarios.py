from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from backend.seguridad import json_error, rol_admin, usuario_actual
from backend.servicios.auth import ErrorNegocio
from backend.servicios.usuario import UsuarioServicio

bp = Blueprint("api_usuarios", __name__, url_prefix="/api/usuarios")
servicio = UsuarioServicio()


@bp.get("")
@rol_admin
def listar_usuarios():
    return jsonify(servicio.listar())


@bp.get("/me")
@jwt_required()
def perfil_actual():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(servicio.perfil(usuario))


@bp.patch("/me")
@jwt_required()
def actualizar_perfil():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 415

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({"error": "El cuerpo JSON debe ser un objeto"}), 400

    try:
        resultado = servicio.actualizar_perfil(usuario, datos)
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)