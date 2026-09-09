from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from backend.seguridad import json_error, usuario_actual
from backend.servicios.auth import ErrorNegocio
from backend.servicios.portafolio import PortafolioServicio

bp = Blueprint("api_portafolio", __name__, url_prefix="/api/portafolio")
servicio = PortafolioServicio()


def _datos_json():
    if not request.is_json:
        return None, (jsonify({"error": "El cuerpo debe ser JSON"}), 415)
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return None, (jsonify({"error": "El cuerpo JSON debe ser un objeto"}), 400)
    return datos, None


@bp.get("")
@jwt_required()
def portafolio_actual():
    usuario = usuario_actual()
    portafolio = servicio.obtener(usuario.id) if usuario else None
    if portafolio is None:
        return jsonify({"error": "Portafolio no encontrado"}), 404
    return jsonify({
        "id": portafolio["id"],
        "saldo_virtual": portafolio["saldo_virtual"],
        "posiciones": portafolio["posiciones"],
    })


@bp.get("/movimientos")
@jwt_required()
def movimientos():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(servicio.listar_movimientos(usuario.id))


@bp.post("/comprar")
@jwt_required()
def comprar():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    datos, error = _datos_json()
    if error:
        return error

    try:
        resultado = servicio.comprar(
            usuario.id,
            datos.get("ticker"),
            datos.get("cantidad"),
            datos.get("precio_unitario"),
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)


@bp.post("/vender")
@jwt_required()
def vender():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    datos, error = _datos_json()
    if error:
        return error

    try:
        resultado = servicio.vender(
            usuario.id,
            datos.get("ticker"),
            datos.get("cantidad"),
            datos.get("precio_unitario"),
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)