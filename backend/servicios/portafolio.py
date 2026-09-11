from decimal import Decimal, InvalidOperation

from sqlalchemy import case, func, select
from sqlalchemy.orm import joinedload

from backend.conexion import db
from backend.modelos import Accion, Movimiento, Portafolio, TipoMovimiento
from backend.servicios.acciones import AccionServicio
from backend.servicios.auth import ErrorNegocio


class PortafolioServicio:
    def obtener(self, usuario_id: int):
        portafolio = self._obtener_portafolio(usuario_id)
        if portafolio is None:
            return None
        return self._estado_portafolio(portafolio)

    def comprar(self, usuario_id: int, ticker: str, cantidad):
        portafolio = self._obtener_portafolio(usuario_id)
        if portafolio is None:
            raise ErrorNegocio("Portafolio no encontrado", 404)

        accion = self._obtener_o_crear_accion(ticker)
        cantidad_decimal = self._parse_decimal(cantidad, "cantidad")
        precio_decimal = self._precio_de_mercado(accion.ticker)
        costo_total = cantidad_decimal * precio_decimal

        if cantidad_decimal <= 0 or precio_decimal <= 0:
            raise ErrorNegocio("La cantidad y el precio deben ser mayores a cero")
        if portafolio.saldo_virtual < costo_total:
            raise ErrorNegocio("Saldo insuficiente para comprar esta cantidad")

        portafolio.saldo_virtual -= costo_total
        movimiento = Movimiento(
            portafolio_id=portafolio.id,
            accion_id=accion.id,
            tipo=TipoMovimiento.compra,
            cantidad=cantidad_decimal,
            precio_unitario=precio_decimal,
        )
        db.session.add(movimiento)
        db.session.commit()
        return self._estado_portafolio(portafolio)

    def vender(self, usuario_id: int, ticker: str, cantidad):
        portafolio = self._obtener_portafolio(usuario_id)
        if portafolio is None:
            raise ErrorNegocio("Portafolio no encontrado", 404)

        accion = self._obtener_accion(ticker)
        cantidad_decimal = self._parse_decimal(cantidad, "cantidad")
        precio_decimal = self._precio_de_mercado(accion.ticker)

        if cantidad_decimal <= 0 or precio_decimal <= 0:
            raise ErrorNegocio("La cantidad y el precio deben ser mayores a cero")

        cantidad_actual = self._cantidad_disponible(portafolio.id, accion.id)
        if cantidad_actual < cantidad_decimal:
            raise ErrorNegocio("No tienes suficientes acciones para vender")

        ingreso_total = cantidad_decimal * precio_decimal
        portafolio.saldo_virtual += ingreso_total
        movimiento = Movimiento(
            portafolio_id=portafolio.id,
            accion_id=accion.id,
            tipo=TipoMovimiento.venta,
            cantidad=cantidad_decimal,
            precio_unitario=precio_decimal,
        )
        db.session.add(movimiento)
        db.session.commit()
        return self._estado_portafolio(portafolio)

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
    def _obtener_portafolio(usuario_id: int):
        return db.session.scalar(
            select(Portafolio).where(Portafolio.usuario_id == usuario_id)
        )

    @staticmethod
    def _obtener_accion(ticker: str):
        ticker = (ticker or "").strip().upper()
        accion = db.session.scalar(select(Accion).where(Accion.ticker == ticker))
        if accion is None:
            raise ErrorNegocio("La acción no existe en el portafolio")
        return accion

    @staticmethod
    def _obtener_o_crear_accion(ticker: str):
        ticker = (ticker or "").strip().upper()
        if not ticker:
            raise ErrorNegocio("El ticker es obligatorio")
        datos_accion = AccionServicio.obtener_por_ticker(ticker)
        if datos_accion is None:
            raise ErrorNegocio("La acción no existe", 404)

        accion = db.session.scalar(select(Accion).where(Accion.ticker == ticker))
        if accion is not None:
            return accion

        accion = Accion(ticker=ticker, nombre_empresa=datos_accion["nombre_empresa"])
        db.session.add(accion)
        db.session.flush()
        return accion

    @staticmethod
    def _precio_de_mercado(ticker: str):
        datos_accion = AccionServicio.obtener_por_ticker(ticker)
        if datos_accion is None:
            raise ErrorNegocio("La acción no existe", 404)
        return PortafolioServicio._parse_decimal(
            datos_accion["precio_actual"], "precio de mercado"
        )

    def _estado_portafolio(self, portafolio):
        return {
            "id": portafolio.id,
            "saldo_virtual": str(portafolio.saldo_virtual),
            "posiciones": self._posiciones(portafolio.id),
            "movimientos": self.listar_movimientos(portafolio.usuario_id),
        }

    @staticmethod
    def _parse_decimal(valor, nombre):
        try:
            decimal_valor = Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError):
            raise ErrorNegocio(f"El campo {nombre} no es válido")
        if not decimal_valor.is_finite():
            raise ErrorNegocio(f"El campo {nombre} no es válido")
        return decimal_valor

    @staticmethod
    def _cantidad_disponible(portafolio_id: int, accion_id: int):
        total = db.session.scalar(
            select(func.coalesce(func.sum(case(
                (Movimiento.tipo == "compra", Movimiento.cantidad),
                else_=-Movimiento.cantidad,
            )), Decimal("0")))
            .where(Movimiento.portafolio_id == portafolio_id)
            .where(Movimiento.accion_id == accion_id)
        )
        return total or Decimal("0")

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