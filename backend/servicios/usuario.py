from werkzeug.security import generate_password_hash

from backend.conexion import db
from backend.modelos import Usuario
from backend.repositorios.usuario import UsuarioRepo
from backend.serializar import usuario_publico
from backend.servicios.auth import AuthServicio, ErrorNegocio


class UsuarioServicio:
    def __init__(self):
        self.usuarios = UsuarioRepo()

    def perfil(self, usuario: Usuario) -> dict:
        return usuario_publico(usuario)

    def actualizar_perfil(self, usuario: Usuario, datos: dict) -> dict:
        nombre = datos.get("nombre")
        correo = datos.get("correo")
        password = datos.get("password")

        if nombre is not None:
            nombre = str(nombre).strip()
            if not nombre or len(nombre) < 2 or len(nombre) > 120:
                raise ErrorNegocio("El nombre debe tener entre 2 y 120 caracteres")
            usuario.nombre = nombre

        if correo is not None:
            correo = str(correo).strip().lower()
            if not correo or not AuthServicio._validar_correo(correo):
                raise ErrorNegocio("El correo no es válido")
            existente = self.usuarios.por_correo(correo)
            if existente is not None and existente.id != usuario.id:
                raise ErrorNegocio("El correo ya está registrado")
            usuario.correo = correo

        if password is not None:
            if not AuthServicio._validar_password(str(password)):
                raise ErrorNegocio(
                    "La contraseña debe tener entre 8 y 32 caracteres, "
                    "mayúscula, minúscula, número y símbolo"
                )
            usuario.password_hash = generate_password_hash(str(password))

        db.session.commit()
        return usuario_publico(usuario)

    def listar(self) -> list[dict]:
        return [usuario_publico(u) for u in self.usuarios.listar()]