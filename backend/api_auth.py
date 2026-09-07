from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, create_access_token

from backend.seguridad import json_error
from backend.servicios.auth import AuthServicio, ErrorNegocio

bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")
servicio = AuthServicio()


@bp.post("/registro")
def registro():
    datos = request.get_json(silent=True) or {}
    try:
        resultado = servicio.registrar(
            datos.get("nombre"), datos.get("correo"), datos.get("password")
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado), 201


@bp.post("/login")
def login():
    datos = request.get_json(silent=True) or {}
    try:
        resultado = servicio.login(datos.get("correo"), datos.get("password"))
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identidad = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=identidad)})