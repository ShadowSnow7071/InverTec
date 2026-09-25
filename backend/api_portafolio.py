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


@bp.get("/movimientos/<int:movimiento_id>")
@jwt_required()
def movimiento_detalle(movimiento_id):
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    try:
        resultado = servicio.obtener_movimiento(usuario.id, movimiento_id)
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)


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
            datos.get("riesgo_calculado"),
            datos.get("password"),
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
            datos.get("riesgo_calculado"),
        )
    except ErrorNegocio as exc:
        return json_error(exc.mensaje, exc.codigo)
    return jsonify(resultado)


@bp.get("/analisis")
@jwt_required()
def analisis_portafolio():
    usuario = usuario_actual()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    portafolio = servicio.obtener(usuario.id)
    if portafolio is None:
        return jsonify({"error": "Portafolio no encontrado"}), 404
    
    from backend.servicios.acciones import AccionServicio
    accion_servicio = AccionServicio()
    movimientos = servicio.listar_movimientos(usuario.id)
    costo_promedio = servicio.costo_promedio_por_ticker(usuario.id)
    
    # Análisis de distribución de activos
    distribucion = {}
    volatilidades = {}
    posiciones_detalle = []
    capital_invertido = 0.0
    
    # Agrupar movimientos más recientes por ticker
    ultimos_movimientos = {}
    for movimiento in movimientos:
        ticker = movimiento["ticker"]
        # Guardar el movimiento más reciente (últimos movimientos están primero)
        if ticker not in ultimos_movimientos:
            ultimos_movimientos[ticker] = movimiento
    
    for posicion in portafolio.get("posiciones", []):
        ticker = posicion["ticker"]
        cantidad = float(posicion["cantidad"])
        accion = accion_servicio.obtener_por_ticker(ticker)
        precio = float(accion["precio_actual"])
        valor_posicion = cantidad * precio
        distribucion[ticker] = valor_posicion

        precio_prom = float(costo_promedio.get(ticker, 0))
        costo_posicion = cantidad * precio_prom
        capital_invertido += costo_posicion
        posiciones_detalle.append({
            "ticker": ticker,
            "nombre_empresa": posicion["nombre_empresa"],
            "cantidad": posicion["cantidad"],
            "precio_promedio": round(precio_prom, 2),
            "precio_actual": precio,
            "valor": round(valor_posicion, 2),
            "ganancia_perdida": round(valor_posicion - costo_posicion, 2),
        })
        
        # Usar el riesgo_nivel del movimiento más reciente de esta acción
        if ticker in ultimos_movimientos:
            riesgo_nivel = ultimos_movimientos[ticker]["riesgo_nivel"]
            volatilidades[ticker] = riesgo_nivel
        else:
            # Si no hay movimientos (no debería ocurrir), marcar como "sin datos"
            volatilidades[ticker] = "bajo"
    
    valor_total_posiciones = sum(distribucion.values())
    ganancia_perdida = valor_total_posiciones - capital_invertido
    
    # Estadísticas de movimientos
    compras = [m for m in movimientos if m["tipo"] == "compra"]
    ventas = [m for m in movimientos if m["tipo"] == "venta"]
    
    return jsonify({
        "saldo_disponible": float(portafolio["saldo_virtual"]),
        "valor_total_posiciones": valor_total_posiciones,
        "capital_invertido": round(capital_invertido, 2),
        "ganancia_perdida": round(ganancia_perdida, 2),
        "ganancia_perdida_porcentaje": round((ganancia_perdida / capital_invertido * 100), 2) if capital_invertido else 0,
        "distribucion_activos": {
            k: float(v) for k, v in distribucion.items()
        } if distribucion else {},
        "cantidad_compras": len(compras),
        "cantidad_ventas": len(ventas),
        "volatilidades": volatilidades,
        "posiciones_count": len(portafolio.get("posiciones", [])),
        "posiciones_detalle": posiciones_detalle,
    })