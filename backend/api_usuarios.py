from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from backend.conexion import db
from backend.modelos import Usuario
from backend.seguridad import json_error, rol_admin, usuario_actual
from backend.servicios.auth import AuthServicio, ErrorNegocio

bp = Blueprint("api_usuarios", __name__, url_prefix="/api/usuarios")
servicio = AuthServicio()


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
        nombre = (datos.get("nombre") or usuario.nombre).strip()
        correo = (datos.get("correo") or usuario.correo).strip().lower()
        password = datos.get("password")

        if not nombre or len(nombre) < 2 or len(nombre) > 120:
            raise ErrorNegocio("El nombre debe tener entre 2 y 120 caracteres")
        if not correo or not servicio._validar_correo(correo):
            raise ErrorNegocio("El correo no es válido")
        if password is not None and not servicio._validar_password(password):
            raise ErrorNegocio(
                "La contraseña debe tener entre 8 y 128 caracteres, "
                "mayúscula, minúscula, número y símbolo"
            )

        existente = db.session.scalar(select(Usuario).where(Usuario.correo == correo))
        if existente is not None and existente.id != usuario.id:
            raise ErrorNegocio("El correo ya está registrado")

        usuario.nombre = nombre
        usuario.correo = correo
        if password is not None:
            usuario.password_hash = generate_password_hash(password)

        db.session.commit()
        return jsonify(
            {
                "id": usuario.id,
                "nombre": usuario.nombre,
                "correo": usuario.correo,
                "rol": usuario.rol.value,
                "saldo_virtual": str(usuario.portafolio.saldo_virtual),
            }
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)