from sqlalchemy import case, func, select
from sqlalchemy.orm import joinedload

from backend.conexion import db
from backend.modelos import Accion, Movimiento, Portafolio


class PortafolioServicio:
    def obtener(self, usuario_id: int):
        portafolio = db.session.scalar(
            select(Portafolio).where(Portafolio.usuario_id == usuario_id)
        )
        if portafolio is None:
            return None

        return {
            "id": portafolio.id,
            "saldo_virtual": str(portafolio.saldo_virtual),
            "posiciones": self._posiciones(portafolio.id),
        }

    def listar_movimientos(self, usuario_id: int):
        movimientos = db.session.scalars(
            select(Movimiento)
            .join(Movimiento.portafolio)
            .options(joinedload(Movimiento.accion))
            .where(Portafolio.usuario_id == usuario_id)
            .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
        ).all()
        return [self._movimiento_dict(movimiento) for movimiento in movimientos]

    @staticmethod
    def _posiciones(portafolio_id):
        cantidad_neta = func.sum(
            case(
                (Movimiento.tipo == "compra", Movimiento.cantidad),
                else_=-Movimiento.cantidad,
            )
        ).label("cantidad")
        filas = db.session.execute(
            select(
                Accion.id,
                Accion.ticker,
                Accion.nombre_empresa,
                cantidad_neta,
            )
            .join(Movimiento, Movimiento.accion_id == Accion.id)
            .where(Movimiento.portafolio_id == portafolio_id)
            .group_by(Accion.id, Accion.ticker, Accion.nombre_empresa)
            .having(cantidad_neta > 0)
            .order_by(Accion.id)
        )

        return [
            {
                "accion_id": accion_id,
                "ticker": ticker,
                "nombre_empresa": nombre_empresa,
                "cantidad": str(cantidad),
            }
            for accion_id, ticker, nombre_empresa, cantidad in filas
        ]

    @staticmethod
    def _movimiento_dict(movimiento):
        return {
            "id": movimiento.id,
            "ticker": movimiento.accion.ticker,
            "nombre_empresa": movimiento.accion.nombre_empresa,
            "tipo": movimiento.tipo.value,
            "cantidad": str(movimiento.cantidad),
            "precio_unitario": str(movimiento.precio_unitario),
            "riesgo_calculado": (
                str(movimiento.riesgo_calculado)
                if movimiento.riesgo_calculado is not None
                else None
            ),
            "fecha": movimiento.fecha.isoformat() if movimiento.fecha else None,
        }