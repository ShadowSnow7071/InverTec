from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from backend.seguridad import usuario_actual

bp = Blueprint("api_usuarios", __name__, url_prefix="/api/usuarios")


@bp.get("/me")
@jwt_required()
def perfil_actual():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(
        {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": usuario.rol.value,
            "saldo_virtual": str(usuario.portafolio.saldo_virtual),
        }
    )