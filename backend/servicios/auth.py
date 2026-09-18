import re
import time

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
    _max_intentos_login = 5
    _ventana_login_segundos = 900
    _intentos_login = {}

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
        ahora = time.monotonic()
        intentos = [
            intento
            for intento in self._intentos_login.get(correo, [])
            if ahora - intento < self._ventana_login_segundos
        ]
        if len(intentos) >= self._max_intentos_login:
            self._intentos_login[correo] = intentos
            raise ErrorNegocio(
                "Demasiados intentos fallidos. Intenta nuevamente más tarde", 429
            )

        usuario = db.session.scalar(select(Usuario).where(Usuario.correo == correo))
        if not usuario or not password or not check_password_hash(usuario.password_hash, password):
            intentos.append(ahora)
            self._intentos_login[correo] = intentos
            raise ErrorNegocio("Correo o contraseña incorrectos", 401)

        self._intentos_login.pop(correo, None)
        return self._respuesta_con_tokens(usuario)

    @staticmethod
    def _validar_correo(correo):
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo))

    @staticmethod
    def _validar_password(password):
        if not password or len(password) < 8 or len(password) > 128:
            return False
        return all(
            re.search(patron, password)
            for patron in (r"[A-Z]", r"[a-z]", r"\d", r"[^A-Za-z0-9]")
        )

    def _validar_datos(self, nombre, correo, password):
        if len(nombre) < 2 or len(nombre) > 120:
            raise ErrorNegocio("El nombre debe tener entre 2 y 120 caracteres")
        if not self._validar_correo(correo):
            raise ErrorNegocio("El correo no es válido")
        if not self._validar_password(password):
            raise ErrorNegocio(
                "La contraseña debe tener entre 8 y 128 caracteres, "
                "mayúscula, minúscula, número y símbolo"
            )

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