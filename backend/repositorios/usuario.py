from sqlalchemy import select

from backend.conexion import db
from backend.modelos import Usuario


class UsuarioRepo:
    def por_id(self, id_usuario: int) -> Usuario | None:
        return db.session.get(Usuario, id_usuario)

    def por_correo(self, correo: str) -> Usuario | None:
        return db.session.execute(
            select(Usuario).where(Usuario.correo == correo)
        ).scalar_one_or_none()

    def listar(self) -> list[Usuario]:
        return list(db.session.scalars(select(Usuario).order_by(Usuario.id)).all())

    def agregar(self, usuario: Usuario) -> Usuario:
        db.session.add(usuario)
        db.session.flush()
        return usuario
