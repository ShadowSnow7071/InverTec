"""agrega la tabla cotizacion, fuente única de precios compartida por todos los workers

Revision ID: 005_cotizacion
Revises: 004_usuario_activo
"""

from alembic import op
import sqlalchemy as sa


revision = "005_cotizacion"
down_revision = "004_usuario_activo"
branch_labels = None
depends_on = None

# Precios de referencia iniciales (los mismos de PRECIOS_BASE). Se copian aquí a
# propósito: una migración debe seguir funcionando aunque el código cambie después.
PRECIOS_INICIALES = {
    "AAPL": "214.20",
    "MSFT": "426.75",
    "GOOGL": "178.90",
    "NVDA": "127.85",
    "AMZN": "192.30",
    "META": "490.50",
    "TSLA": "252.10",
    "NFLX": "643.20",
    "AMD": "165.45",
}


def upgrade():
    cotizacion = op.create_table(
        "cotizacion",
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("precio", sa.Numeric(12, 2), nullable=False),
        sa.Column("cambio_porcentaje", sa.Numeric(7, 2), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=True),
        sa.Column("ultimo_intento_en", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("ticker"),
    )
    # actualizado_en queda en NULL: significa "todavía no hay dato real", así que la
    # app los marca como simulados hasta que el primer refresco traiga datos reales.
    op.bulk_insert(
        cotizacion,
        [{"ticker": ticker, "precio": precio} for ticker, precio in PRECIOS_INICIALES.items()],
    )


def downgrade():
    op.drop_table("cotizacion")
