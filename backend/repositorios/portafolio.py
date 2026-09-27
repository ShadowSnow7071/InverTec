from backend.conexion import db
from backend.modelos import Portafolio


class PortafolioRepo:
    def agregar_para_usuario(self, usuario_id: int) -> Portafolio:
        portafolio = Portafolio(usuario_id=usuario_id)
        db.session.add(portafolio)
        db.session.flush()
        return portafolio
