from werkzeug.security import generate_password_hash

from backend.conexion import db
from backend.modelos import Usuario
from backend.repositorios.usuario import UsuarioRepo
from backend.serializar import usuario_publico
from backend.servicios.auth import ErrorNegocio


class UsuarioServicio:
    def __init__(self):
        self.usuarios = UsuarioRepo()

    def perfil(self, usuario: Usuario) -> dict:
        return usuario_publico(usuario)

    def actualizar_perfil(self, usuario: Usuario, datos: dict) -> dict:
        nombre = datos.get("nombre")
        password = datos.get("password")
        if nombre is None and password is None:
            raise ErrorNegocio("Indica nombre o contraseña para actualizar", 400)
        if nombre is not None:
            nombre = str(nombre).strip()
            if not nombre:
                raise ErrorNegocio("El nombre no puede estar vacío", 400)
            usuario.nombre = nombre
        if password is not None:
            if len(str(password)) < 8:
                raise ErrorNegocio("La contraseña debe tener al menos 8 caracteres", 400)
            usuario.password_hash = generate_password_hash(str(password))
        db.session.commit()
        return usuario_publico(usuario)

    def listar(self) -> list[dict]:
        return [usuario_publico(u) for u in self.usuarios.listar()]
