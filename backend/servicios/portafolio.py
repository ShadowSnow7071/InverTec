from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from backend.conexion import db
from backend.modelos import Movimiento, Portafolio, TipoMovimiento


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
            "posiciones": self._posiciones(portafolio),
        }

    def listar_movimientos(self, usuario_id: int):
        movimientos = db.session.scalars(
            select(Movimiento)
            .join(Movimiento.portafolio)
            .where(Portafolio.usuario_id == usuario_id)
            .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
        ).all()
        return [self._movimiento_dict(movimiento) for movimiento in movimientos]

    @staticmethod
    def _posiciones(portafolio):
        acumulado = defaultdict(lambda: Decimal("0"))
        acciones = {}
        for movimiento in portafolio.movimientos:
            signo = Decimal("1") if movimiento.tipo == TipoMovimiento.compra else Decimal("-1")
            acumulado[movimiento.accion_id] += signo * movimiento.cantidad
            acciones[movimiento.accion_id] = movimiento.accion

        return [
            {
                "accion_id": accion_id,
                "ticker": acciones[accion_id].ticker,
                "nombre_empresa": acciones[accion_id].nombre_empresa,
                "cantidad": str(cantidad),
            }
            for accion_id, cantidad in sorted(acumulado.items())
            if cantidad > 0
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