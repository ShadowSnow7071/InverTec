from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import (
    current_user,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from backend.servicios.auth import AuthServicio, ErrorNegocio
from backend.servicios.portafolio import PortafolioServicio

bp = Blueprint("main", __name__)
auth = AuthServicio()
portafolio = PortafolioServicio()


@bp.get("/")
@jwt_required(optional=True)
def index():
    return render_template("index.html", usuario_actual=current_user)


@bp.get("/registro")
@jwt_required(optional=True)
def registro_form():
    if current_user:
        return redirect(url_for("main.perfil"))
    return render_template("registro.html")


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
@jwt_required(optional=True)
def login_form():
    if current_user:
        return redirect(url_for("main.perfil"))
    return render_template("login.html")


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
    return render_template(
        "perfil.html",
        usuario_actual=usuario,
        datos_portafolio=datos_portafolio,
        movimientos=movimientos,
    )


@bp.post("/logout")
def logout():
    respuesta = redirect(url_for("main.index"))
    unset_jwt_cookies(respuesta)
    return respuesta


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})
