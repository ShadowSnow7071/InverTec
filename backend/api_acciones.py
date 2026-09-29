from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from backend.seguridad import json_error, rol_admin, usuario_actual
from backend.servicios.acciones import AccionServicio
from backend.servicios.auth import ErrorNegocio

bp = Blueprint("api_acciones", __name__, url_prefix="/api")
servicio = AccionServicio()


@bp.get("/acciones")
def acciones():
    return jsonify(servicio.listar_catalogo())


@bp.post("/acciones/actualizar")
@rol_admin
def actualizar_acciones():

    resumen, error = servicio.refrescar_manual()
    if error is not None:
        codigo = 429 if error.startswith("Espera") else 503
        return json_error(error, codigo)

    ultima = servicio.ultima_actualizacion()
    return jsonify(
        {
            "actualizadas": resumen["actualizadas"],
            "fallidas": resumen["fallidas"],
            "ultima_actualizacion": ultima.isoformat() + "Z" if ultima else None,
        }
    )


@bp.get("/acciones/<ticker>")
@bp.get("/acciones/<ticker>/precio")
def detalle_accion(ticker):
    accion = servicio.obtener_por_ticker(ticker)
    if accion is None:
        return jsonify({"error": "Acción no encontrada"}), 404

    if request.path.endswith("/precio"):
        return jsonify(
            {
                "ticker": accion["ticker"],
                "nombre_empresa": accion["nombre_empresa"],
                "precio_actual": accion["precio_actual"],
            }
        )

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
            usuario.portafolio.saldo_virtual,
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)

    return jsonify(resultado)
