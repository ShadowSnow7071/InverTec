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

from backend.servicios.acciones import AccionServicio
from backend.servicios.auth import AuthServicio, ErrorNegocio
from backend.servicios.portafolio import PortafolioServicio

bp = Blueprint("main", __name__)
auth = AuthServicio()
acciones = AccionServicio()
portafolio = PortafolioServicio()


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
    return _respuesta_publica("index.html", usuario, limpiar_cookies)


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

    respuesta = redirect(url_for("main.perfil"))
    set_access_cookies(respuesta, resultado["access_token"])
    set_refresh_cookies(respuesta, resultado["refresh_token"])
    return respuesta


@bp.get("/login")
def login_form():
    usuario, limpiar_cookies = _usuario_publico()
    if usuario:
        return redirect(url_for("main.perfil"))
    return _respuesta_publica("login.html", usuario, limpiar_cookies)


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
    catalogo = acciones.listar_catalogo(precios_reales=False)
    return render_template(
        "perfil.html",
        usuario_actual=usuario,
        datos_portafolio=datos_portafolio,
        movimientos=movimientos,
        catalogo=catalogo,
    )


@bp.post("/logout")
def logout():
    respuesta = redirect(url_for("main.index"))
    unset_jwt_cookies(respuesta)
    return respuesta


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})
