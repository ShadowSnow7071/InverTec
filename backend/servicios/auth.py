import re

from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from backend.conexion import db
from backend.modelos import Portafolio, Usuario


class ErrorNegocio(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        self.mensaje = mensaje
        self.codigo = codigo


class AuthServicio:
    def registrar(self, nombre, correo, password):
        nombre = (nombre or "").strip()
        correo = (correo or "").strip().lower()
        self._validar_datos(nombre, correo, password)

        existente = db.session.scalar(select(Usuario).where(Usuario.correo == correo))
        if existente:
            raise ErrorNegocio("El correo ya está registrado")

        usuario = Usuario(
            nombre=nombre,
            correo=correo,
            password_hash=generate_password_hash(password),
        )
        usuario.portafolio = Portafolio()
        db.session.add(usuario)
        db.session.commit()
        return self._respuesta_con_tokens(usuario)

    def login(self, correo, password):
        correo = (correo or "").strip().lower()
        usuario = db.session.scalar(select(Usuario).where(Usuario.correo == correo))
        if not usuario or not password or not check_password_hash(usuario.password_hash, password):
            raise ErrorNegocio("Correo o contraseña incorrectos", 401)
        return self._respuesta_con_tokens(usuario)

    def _validar_datos(self, nombre, correo, password):
        if len(nombre) < 2 or len(nombre) > 120:
            raise ErrorNegocio("El nombre debe tener entre 2 y 120 caracteres")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            raise ErrorNegocio("El correo no es válido")
        if not password or len(password) < 8:
            raise ErrorNegocio("La contraseña debe tener al menos 8 caracteres")

    def _respuesta_con_tokens(self, usuario):
        identidad = str(usuario.id)
        claims = {"rol": usuario.rol.value}
        return {
            "access_token": create_access_token(identity=identidad, additional_claims=claims),
            "refresh_token": create_refresh_token(identity=identidad, additional_claims=claims),
            "usuario": self._usuario_dict(usuario),
        }

    @staticmethod
    def _usuario_dict(usuario):
        return {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": usuario.rol.value,
        }