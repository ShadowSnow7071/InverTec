from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from backend.seguridad import json_error, rol_admin, usuario_actual
from backend.servicios.auth import ErrorNegocio
from backend.servicios.portafolio import PortafolioServicio
from backend.servicios.usuario import UsuarioServicio

bp = Blueprint("api_usuarios", __name__, url_prefix="/api/usuarios")
servicio = UsuarioServicio()
portafolio_servicio = PortafolioServicio()


@bp.get("")
@rol_admin
def listar_usuarios():
    return jsonify(servicio.listar())


@bp.get("/estadisticas")
@rol_admin
def estadisticas():
    return jsonify(servicio.estadisticas())


@bp.get("/auditoria")
@rol_admin
def auditoria():
    return jsonify(portafolio_servicio.listar_movimientos_todos())


@bp.patch("/<int:usuario_id>/estado")
@rol_admin
def cambiar_estado(usuario_id):
    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 415
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not isinstance(datos.get("activo"), bool):
        return jsonify({"error": "El campo 'activo' es requerido y debe ser booleano"}), 400
    try:
        resultado = servicio.cambiar_estado(usuario_id, datos["activo"], usuario_actual())
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)


@bp.patch("/<int:usuario_id>/rol")
@rol_admin
def cambiar_rol(usuario_id):
    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 415
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not datos.get("rol"):
        return jsonify({"error": "El campo 'rol' es requerido"}), 400
    try:
        resultado = servicio.cambiar_rol(usuario_id, datos["rol"], usuario_actual())
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)


@bp.delete("/<int:usuario_id>")
@rol_admin
def eliminar_usuario(usuario_id):
    try:
        servicio.eliminar(usuario_id, usuario_actual())
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return "", 204


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