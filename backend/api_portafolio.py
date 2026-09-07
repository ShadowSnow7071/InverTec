from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from backend.seguridad import usuario_actual
from backend.servicios.portafolio import PortafolioServicio

bp = Blueprint("api_portafolio", __name__, url_prefix="/api/portafolio")
servicio = PortafolioServicio()


@bp.get("")
@jwt_required()
def portafolio_actual():
    usuario = usuario_actual()
    portafolio = servicio.obtener(usuario.id) if usuario else None
    if portafolio is None:
        return jsonify({"error": "Portafolio no encontrado"}), 404
    return jsonify(portafolio)


@bp.get("/movimientos")
@jwt_required()
def movimientos():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(servicio.listar_movimientos(usuario.id))