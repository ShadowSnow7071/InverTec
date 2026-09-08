from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from backend.seguridad import json_error, usuario_actual
from backend.servicios.acciones import AccionServicio
from backend.servicios.auth import ErrorNegocio

bp = Blueprint("api_acciones", __name__, url_prefix="/api")
servicio = AccionServicio()


@bp.get("/acciones")
def acciones():
    return jsonify(servicio.listar_catalogo())


@bp.get("/acciones/<ticker>")
def detalle_accion(ticker):
    accion = servicio.obtener_por_ticker(ticker)
    if accion is None:
        return jsonify({"error": "Acción no encontrada"}), 404
    return jsonify(accion)


@bp.post("/portafolio/movimientos/riesgo")
@jwt_required()
def riesgo_movimiento():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 415

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({"error": "El cuerpo JSON debe ser un objeto"}), 400

    try:
        resultado = servicio.calcular_riesgo(
            datos.get("ticker"),
            datos.get("cantidad"),
            datos.get("precio_unitario"),
            usuario.portafolio.saldo_virtual,
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)

    return jsonify(resultado)
