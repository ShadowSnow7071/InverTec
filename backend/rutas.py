from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import (
    current_user,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from backend.servicios.auth import AuthServicio, ErrorNegocio

bp = Blueprint("main", __name__)
auth = AuthServicio()


@bp.get("/")
@jwt_required(optional=True)
def index():
    return render_template("index.html")


@bp.get("/health")
def health():
    from flask import jsonify

    return jsonify({"status": "ok"})


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
        return render_template("registro.html"), exc.codigo if exc.codigo != 401 else 400
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
        resultado = auth.login(request.form.get("correo"), request.form.get("password"))
    except ErrorNegocio as exc:
        flash(exc.mensaje, "danger")
        return render_template("login.html"), 401
    respuesta = redirect(url_for("main.perfil"))
    set_access_cookies(respuesta, resultado["access_token"])
    set_refresh_cookies(respuesta, resultado["refresh_token"])
    return respuesta


@bp.get("/perfil")
@jwt_required(optional=True)
def perfil():
    if current_user is None:
        return redirect(url_for("main.login_form"))
    return render_template("perfil.html", usuario_actual=current_user)


@bp.post("/logout")
def logout():
    respuesta = redirect(url_for("main.index"))
    unset_jwt_cookies(respuesta)
    return respuesta
