"""agrega tokens de recuperación de contraseña

Revision ID: 002_tokens_recuperacion
Revises: 001_esquema_inicial
"""

from alembic import op
import sqlalchemy as sa


revision = "002_tokens_recuperacion"
down_revision = "001_esquema_inicial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_recuperacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_en", sa.DateTime(), nullable=False),
        sa.Column("usado_en", sa.DateTime(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade():
    op.drop_table("token_recuperacion")