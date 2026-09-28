import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
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
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )

    portafolio: Mapped["Portafolio | None"] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    tokens_recuperacion: Mapped[list["TokenRecuperacion"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class TokenRecuperacion(db.Model):
    __tablename__ = "token_recuperacion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usado_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    usuario: Mapped[Usuario] = relationship(back_populates="tokens_recuperacion")


class Portafolio(db.Model):
    __tablename__ = "portafolio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id"), unique=True, nullable=False
    )
    saldo_virtual: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("50000.00"),
        server_default="50000.00",
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    usuario: Mapped[Usuario] = relationship(back_populates="portafolio")
    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="portafolio", cascade="all, delete-orphan"
    )


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

class Cotizacion(db.Model):
    """Última cotización conocida de cada acción del catálogo.

    Es la ÚNICA fuente de precios de la app: Mercado, Simular, Inicio, Análisis
    y la ejecución de compras/ventas leen de aquí, así todos los workers de
    Gunicorn ven exactamente el mismo valor. Solo el proceso de refresco
    (ver AccionServicio.refrescar_cotizaciones) escribe en esta tabla.
    """

    __tablename__ = "cotizacion"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cambio_porcentaje: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    # Momento (UTC) en que se obtuvo el dato REAL de Alpha Vantage. NULL significa
    # que nunca se ha obtenido: el precio es el de referencia simulado.
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime)
    # Último intento de refresco (con o sin éxito). Evita reintentar en cada
    # visita cuando Alpha Vantage está fallando o se agotó el límite diario.
    ultimo_intento_en: Mapped[datetime | None] = mapped_column(DateTime)
