import re
import time
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from flask_jwt_extended import create_access_token, create_refresh_token
import resend
from sqlalchemy import delete, select
from werkzeug.security import check_password_hash, generate_password_hash

from backend.conexion import db
from backend.modelos import TokenRecuperacion, Usuario
from backend.repositorios.portafolio import PortafolioRepo


logger = logging.getLogger(__name__)


class ErrorNegocio(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        self.mensaje = mensaje
        self.codigo = codigo


class AuthServicio:
    _max_intentos_login = 5
    _ventana_login_segundos = 900
    _intentos_login = {}

    @staticmethod
    def _ahora_utc():
        return datetime.now(timezone.utc).replace(tzinfo=None)

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
        db.session.add(usuario)
        db.session.flush()
        PortafolioRepo().agregar_para_usuario(usuario.id)
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

    def solicitar_recuperacion(self, correo, base_url, api_key, from_email):
        if not api_key or not from_email:
            raise ErrorNegocio("El servicio de correo no está configurado", 503)
        correo = (correo or "").strip().lower()
        usuario = db.session.scalar(select(Usuario).where(Usuario.correo == correo))
        if usuario is None:
            return

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expira_en = self._ahora_utc() + timedelta(minutes=30)
        db.session.execute(
            delete(TokenRecuperacion).where(
                TokenRecuperacion.usuario_id == usuario.id,
                TokenRecuperacion.usado_en.is_(None),
            )
        )
        db.session.add(
            TokenRecuperacion(
                usuario_id=usuario.id,
                token_hash=token_hash,
                expira_en=expira_en,
            )
        )
        try:
            self._enviar_correo_recuperacion(
                usuario.correo,
                usuario.nombre,
                f"{base_url}/restablecer-password?token={token}",
                api_key,
                from_email,
            )
        except ErrorNegocio:
            db.session.rollback()
            raise
        db.session.commit()

    def restablecer_password(self, token, password):
        if not token or not self._validar_password(password):
            raise ErrorNegocio("El token o la contraseña no son válidos")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        recuperacion = db.session.scalar(
            select(TokenRecuperacion).where(TokenRecuperacion.token_hash == token_hash)
        )
        if (
            recuperacion is None
            or recuperacion.usado_en is not None
            or recuperacion.expira_en <= self._ahora_utc()
        ):
            raise ErrorNegocio("El token de recuperación no es válido o expiró")

        recuperacion.usuario.password_hash = generate_password_hash(password)
        recuperacion.usado_en = self._ahora_utc()
        db.session.commit()

    @staticmethod
    def _enviar_correo_recuperacion(destinatario, nombre, enlace, api_key, from_email):
        if not api_key or not from_email:
            raise ErrorNegocio("El servicio de correo no está configurado", 503)
        cuerpo = {
            "from": from_email,
            "to": [destinatario],
            "subject": "Restablece tu contraseña de InverTec",
            "html": (
                f"<p>Hola, {nombre}.</p>"
                f"<p>Usa este enlace para restablecer tu contraseña:</p>"
                f"<p><a href=\"{enlace}\">Restablecer contraseña</a></p>"
                "<p>El enlace expira en 30 minutos.</p>"
            ),
        }
        resend.api_key = api_key
        try:
            resend.Emails.send(cuerpo)
        except Exception as exc:
            logger.warning("Resend rechazó el correo: %s", exc)
            raise ErrorNegocio("No fue posible enviar el correo", 503) from exc

    @staticmethod
    def _validar_correo(correo):
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo))

    @staticmethod
    def _validar_password(password):
        if not password or len(password) < 8 or len(password) > 32:
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
                "La contraseña debe tener entre 8 y 32 caracteres, "
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