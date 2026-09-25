"""agrega columna activo a usuario, para bloqueo de cuentas desde admin

Revision ID: 004_usuario_activo
Revises: 003_saldo_inicial_50000
"""

from alembic import op
import sqlalchemy as sa


revision = "004_usuario_activo"
down_revision = "003_saldo_inicial_50000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "usuario",
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade():
    op.drop_column("usuario", "activo")
