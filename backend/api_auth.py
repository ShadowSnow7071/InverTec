from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required, set_access_cookies, set_refresh_cookies

from backend.seguridad import json_error
from backend.servicios.auth import AuthServicio, ErrorNegocio

bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")
servicio = AuthServicio()


def _aplicar_cookies(cuerpo: dict, codigo: int = 200):
    respuesta = jsonify(cuerpo)
    respuesta.status_code = codigo
    set_access_cookies(respuesta, cuerpo["access_token"])
    if "refresh_token" in cuerpo:
        set_refresh_cookies(respuesta, cuerpo["refresh_token"])
    return respuesta


@bp.post("/registro")
def registro():
    datos = request.get_json(silent=True) or {}
    try:
        resultado = servicio.registrar(
            datos.get("nombre"),
            datos.get("correo"),
            datos.get("password"),
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return _aplicar_cookies(resultado, 201)


@bp.post("/login")
def login():
    datos = request.get_json(silent=True) or {}
    try:
        resultado = servicio.login(datos.get("correo"), datos.get("password"))
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return _aplicar_cookies(resultado)


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    if current_user is None:
        return json_error("Token inválido", 401)
    return _aplicar_cookies(servicio.renovar(current_user))
