from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required

from backend.seguridad import json_error
from backend.servicios.auth import AuthServicio, ErrorNegocio

bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")
servicio = AuthServicio()


def _datos_json():
    if not request.is_json:
        return None, (jsonify({"error": "El cuerpo debe ser JSON"}), 415)
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return None, (jsonify({"error": "El cuerpo JSON debe ser un objeto"}), 400)
    return datos, None


@bp.post("/registro")
def registro():
    datos, error = _datos_json()
    if error:
        return error
    try:
        resultado = servicio.registrar(
            datos.get("nombre"), datos.get("correo"), datos.get("password")
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado), 201


@bp.post("/login")
def login():
    datos, error = _datos_json()
    if error:
        return error
    try:
        ip_cliente = request.remote_addr
        resultado = servicio.login(datos.get("correo"), datos.get("password"), ip_cliente)
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)


@bp.post("/recuperar-password")
def solicitar_recuperacion():
    datos, error = _datos_json()
    if error:
        return error
    try:
        servicio.solicitar_recuperacion(
            datos.get("correo"),
            current_app.config["APP_BASE_URL"],
            current_app.config.get("RESEND_API_KEY"),
            current_app.config.get("RESEND_FROM_EMAIL"),
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify({"mensaje": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"})


@bp.post("/restablecer-password")
def restablecer_password():
    datos, error = _datos_json()
    if error:
        return error
    try:
        servicio.restablecer_password(datos.get("token"), datos.get("password"))
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify({"mensaje": "La contraseña fue actualizada correctamente"})


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identidad = get_jwt_identity()
    return jsonify({
        "access_token": create_access_token(
            identity=identidad,
            additional_claims={"rol": get_jwt().get("rol")},
        )
    })