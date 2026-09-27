"""esquema inicial

Revision ID: 001_esquema_inicial
Revises:
Create Date: 2026-09-02

"""

from alembic import op
import sqlalchemy as sa

revision = "001_esquema_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("correo", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum(
                "inversionista",
                "administrador",
                name="rol_usuario",
            ),
            nullable=False,
            server_default="inversionista",
        ),
        sa.Column(
            "fecha_registro",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correo"),
    )
    op.create_table(
        "portafolio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "saldo_virtual",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="10000.00",
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id"),
    )
    op.create_table(
        "accion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("nombre_empresa", sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )
    op.create_table(
        "movimiento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portafolio_id", sa.Integer(), nullable=False),
        sa.Column("accion_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum("compra", "venta", name="tipo_movimiento"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column(
            "precio_unitario", sa.Numeric(precision=12, scale=2), nullable=False
        ),
        sa.Column("riesgo_calculado", sa.Numeric(precision=5, scale=2)),
        sa.Column(
            "fecha",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["accion_id"], ["accion.id"]),
        sa.ForeignKeyConstraint(["portafolio_id"], ["portafolio.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("movimiento")
    op.drop_table("accion")
    op.drop_table("portafolio")
    op.drop_table("usuario")
