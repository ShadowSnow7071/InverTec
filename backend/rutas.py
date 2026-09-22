from flask import Blueprint, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_jwt_extended import (
    current_user,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)
from backend.seguridad import rol_admin
from backend.servicios.acciones import AccionServicio
from backend.servicios.auth import AuthServicio, ErrorNegocio
from backend.servicios.portafolio import PortafolioServicio
from backend.servicios.usuario import UsuarioServicio

bp = Blueprint("main", __name__)
auth = AuthServicio()
acciones = AccionServicio()
portafolio = PortafolioServicio()
usuarios = UsuarioServicio()


@bp.get("/favicon.ico")
def favicon():
    return "", 204


def _usuario_publico():
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None, True
    return current_user, False


def _respuesta_publica(templateo, usuario, limpiar_cookies, **contexto):
    respuesta = make_response(render_template(templateo, usuario_actual=usuario, **contexto))
    if limpiar_cookies:
        unset_jwt_cookies(respuesta)
    return respuesta


@bp.get("/")
def index():
    usuario, limpiar_cookies = _usuario_publico()
    if usuario:
        return redirect(url_for("main.perfil"))
    return _respuesta_publica("login.html", usuario, limpiar_cookies)


@bp.get("/registro")
def registro_form():
    usuario, limpiar_cookies = _usuario_publico()
    if usuario:
        return redirect(url_for("main.perfil"))
    return _respuesta_publica("registro.html", usuario, limpiar_cookies)


@bp.post("/registro")
def registro_post():
    try:
        resultado = auth.registrar(
            request.form.get("nombre"),
            request.form.get("correo"),
            request.form.get("password"),
        )
    except ErrorNegocio as exc:
        flash(exc.mensaje, "danger")
        return render_template("registro.html"), exc.codigo

    respuesta = redirect(url_for("main.perfil", bienvenida=1))
    set_access_cookies(respuesta, resultado["access_token"])
    set_refresh_cookies(respuesta, resultado["refresh_token"])
    return respuesta


@bp.get("/login")
def login_form():
    usuario, limpiar_cookies = _usuario_publico()
    if usuario:
        return redirect(url_for("main.perfil"))
    return _respuesta_publica("login.html", usuario, limpiar_cookies)


@bp.get("/recuperar-password")
def recuperar_password_form():
    usuario, limpiar_cookies = _usuario_publico()
    return _respuesta_publica("recuperar_password.html", usuario, limpiar_cookies)


@bp.get("/restablecer-password")
def restablecer_password_form():
    usuario, limpiar_cookies = _usuario_publico()
    return _respuesta_publica("restablecer_password.html", usuario, limpiar_cookies)


@bp.post("/login")
def login_post():
    try:
        resultado = auth.login(
            request.form.get("correo"),
            request.form.get("password"),
        )
    except ErrorNegocio as exc:
        flash(exc.mensaje, "danger")
        return render_template("login.html"), exc.codigo

    respuesta = redirect(url_for("main.perfil"))
    set_access_cookies(respuesta, resultado["access_token"])
    set_refresh_cookies(respuesta, resultado["refresh_token"])
    return respuesta


@bp.get("/perfil")
@jwt_required()
def perfil():
    usuario = current_user
    datos_portafolio = portafolio.obtener(int(get_jwt_identity()))
    movimientos = portafolio.listar_movimientos(int(get_jwt_identity()))

    valor_posiciones = 0
    for posicion in datos_portafolio["posiciones"]:
        accion = acciones.obtener_por_ticker(posicion["ticker"])
        if accion:
            valor_posiciones += float(posicion["cantidad"]) * float(accion["precio_actual"])

    return render_template(
        "inicio.html",
        seccion_activa="inicio",
        usuario_actual=usuario,
        datos_portafolio=datos_portafolio,
        valor_posiciones=f"{valor_posiciones:,.2f}",
        total_compras=sum(1 for m in movimientos if m["tipo"] == "compra"),
        total_ventas=sum(1 for m in movimientos if m["tipo"] == "venta"),
    )


@bp.get("/mercado")
@jwt_required()
def mercado():
    usuario = current_user
    catalogo = acciones.listar_catalogo(precios_reales=True)
    return render_template(
        "mercado.html",
        seccion_activa="mercado",
        usuario_actual=usuario,
        catalogo=catalogo,
    )


@bp.get("/historial")
@jwt_required()
def historial():
    usuario = current_user
    movimientos = portafolio.listar_movimientos(int(get_jwt_identity()))
    return render_template(
        "historial.html",
        seccion_activa="historial",
        usuario_actual=usuario,
        movimientos=movimientos,
        total_compras=sum(1 for m in movimientos if m["tipo"] == "compra"),
        total_ventas=sum(1 for m in movimientos if m["tipo"] == "venta"),
    )


@bp.get("/simular")
@jwt_required()
def simular():
    usuario = current_user
    catalogo = acciones.listar_catalogo(precios_reales=False)
    return render_template(
        "simular.html",
        seccion_activa="simular",
        usuario_actual=usuario,
        catalogo=catalogo,
        ticker_inicial=request.args.get("ticker", "").upper(),
        operacion_inicial=request.args.get("operacion", "comprar"),
    )


@bp.get("/analisis")
@jwt_required()
def analisis():
    usuario = current_user
    datos_portafolio = portafolio.obtener(int(get_jwt_identity()))
    return render_template(
        "analisis.html",
        seccion_activa="analisis",
        usuario_actual=usuario,
        datos_portafolio=datos_portafolio,
    )


@bp.get("/configuracion")
@jwt_required()
def configuracion():
    usuario = current_user
    return render_template("configuracion.html", usuario_actual=usuario)


@bp.get("/admin/usuarios")
@rol_admin
def admin_usuarios():
    return render_template(
        "admin_usuarios.html",
        usuario_actual=current_user,
        usuarios=usuarios.listar(),
    )


@bp.post("/logout")
def logout():
    respuesta = redirect(url_for("main.index"))
    unset_jwt_cookies(respuesta)
    return respuesta


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})