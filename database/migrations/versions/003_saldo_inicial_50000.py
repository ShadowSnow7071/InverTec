"""sube el saldo virtual inicial de 10000 a 50000

Revision ID: 003_saldo_inicial_50000
Revises: 002_tokens_recuperacion
"""

from alembic import op
import sqlalchemy as sa


revision = "003_saldo_inicial_50000"
down_revision = "002_tokens_recuperacion"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "portafolio",
        "saldo_virtual",
        server_default="50000.00",
        existing_type=sa.Numeric(12, 2),
        existing_nullable=False,
    )
    op.execute("UPDATE portafolio SET saldo_virtual = 50000.00")


def downgrade():
    op.alter_column(
        "portafolio",
        "saldo_virtual",
        server_default="10000.00",
        existing_type=sa.Numeric(12, 2),
        existing_nullable=False,
    )
    op.execute("UPDATE portafolio SET saldo_virtual = 10000.00")