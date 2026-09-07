from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import check_password_hash, generate_password_hash

from backend.conexion import db
from backend.modelos import RolUsuario, Usuario
from backend.repositorios.portafolio import PortafolioRepo
from backend.repositorios.usuario import UsuarioRepo
from backend.serializar import usuario_publico


class ErrorNegocio(Exception):
    def __init__(self, mensaje: str, codigo: int):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class AuthServicio:
    def __init__(self):
        self.usuarios = UsuarioRepo()
        self.portafolios = PortafolioRepo()

    def registrar(self, nombre: str, correo: str, password: str) -> dict:
        nombre = (nombre or "").strip()
        correo = (correo or "").strip().lower()
        password = password or ""
        if not nombre or not correo or not password:
            raise ErrorNegocio("Nombre, correo y contraseña son obligatorios", 400)
        if len(password) < 8:
            raise ErrorNegocio("La contraseña debe tener al menos 8 caracteres", 400)
        if self.usuarios.por_correo(correo):
            raise ErrorNegocio("El correo ya está registrado", 400)

        usuario = Usuario(
            nombre=nombre,
            correo=correo,
            password_hash=generate_password_hash(password),
            rol=RolUsuario.inversionista,
        )
        self.usuarios.agregar(usuario)
        self.portafolios.agregar_para_usuario(usuario.id)
        db.session.commit()
        return self._respuesta_con_tokens(usuario)

    def login(self, correo: str, password: str) -> dict:
        correo = (correo or "").strip().lower()
        usuario = self.usuarios.por_correo(correo)
        if usuario is None or not check_password_hash(usuario.password_hash, password or ""):
            raise ErrorNegocio("Credenciales inválidas", 401)
        return self._respuesta_con_tokens(usuario)

    def renovar(self, usuario: Usuario) -> dict:
        return {
            "access_token": self._access(usuario),
            "usuario": usuario_publico(usuario),
        }

    def _access(self, usuario: Usuario) -> str:
        return create_access_token(
            identity=str(usuario.id),
            additional_claims={"rol": usuario.rol.value},
        )

    def _refresh(self, usuario: Usuario) -> str:
        return create_refresh_token(
            identity=str(usuario.id),
            additional_claims={"rol": usuario.rol.value},
        )

    def _respuesta_con_tokens(self, usuario: Usuario) -> dict:
        return {
            "access_token": self._access(usuario),
            "refresh_token": self._refresh(usuario),
            "usuario": usuario_publico(usuario),
        }
