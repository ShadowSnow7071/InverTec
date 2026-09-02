import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.conexion import db


class RolUsuario(enum.Enum):
    inversionista = "inversionista"
    administrador = "administrador"


class TipoMovimiento(enum.Enum):
    compra = "compra"
    venta = "venta"


class Usuario(db.Model):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    correo: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        Enum(
            RolUsuario,
            name="rol_usuario",
            values_callable=lambda items: [item.value for item in items],
        ),
        nullable=False,
        default=RolUsuario.inversionista,
        server_default="inversionista",
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    portafolio: Mapped["Portafolio | None"] = relationship(
        back_populates="usuario", uselist=False
    )


class Portafolio(db.Model):
    __tablename__ = "portafolio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id"), unique=True, nullable=False
    )
    saldo_virtual: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("10000.00"),
        server_default="10000.00",
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    usuario: Mapped[Usuario] = relationship(back_populates="portafolio")
    movimientos: Mapped[list["Movimiento"]] = relationship(back_populates="portafolio")


class Accion(db.Model):
    __tablename__ = "accion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre_empresa: Mapped[str] = mapped_column(String(150), nullable=False)

    movimientos: Mapped[list["Movimiento"]] = relationship(back_populates="accion")


class Movimiento(db.Model):
    __tablename__ = "movimiento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portafolio_id: Mapped[int] = mapped_column(
        ForeignKey("portafolio.id"), nullable=False
    )
    accion_id: Mapped[int] = mapped_column(ForeignKey("accion.id"), nullable=False)
    tipo: Mapped[TipoMovimiento] = mapped_column(
        Enum(
            TipoMovimiento,
            name="tipo_movimiento",
            values_callable=lambda items: [item.value for item in items],
        ),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    riesgo_calculado: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    portafolio: Mapped[Portafolio] = relationship(back_populates="movimientos")
    accion: Mapped[Accion] = relationship(back_populates="movimientos")
