from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import select

from backend.conexion import db
from backend.modelos import Usuario
from backend.seguridad import json_error, rol_admin, usuario_actual

bp = Blueprint("api_usuarios", __name__, url_prefix="/api/usuarios")


@bp.get("")
@rol_admin
def listar_usuarios():
    usuarios = db.session.scalars(select(Usuario).order_by(Usuario.id)).all()
    return jsonify(
        [
            {
                "id": usuario.id,
                "nombre": usuario.nombre,
                "correo": usuario.correo,
                "rol": usuario.rol.value,
                "saldo_virtual": str(usuario.portafolio.saldo_virtual)
                if usuario.portafolio is not None
                else None,
            }
            for usuario in usuarios
        ]
    )


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