"""Esquema inicial: usuarios, empresas, productos, ventas, compras, gastos, importaciones y v_ventas_diarias.

Revision ID: 0001
Revises:
Create Date: 2026-10-06
"""

from alembic import op
from sqlalchemy import text

from app.db.models import VISTA_VENTAS_DIARIAS, metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata.create_all(bind)
    bind.execute(text("DROP VIEW IF EXISTS v_ventas_diarias"))
    bind.execute(text(VISTA_VENTAS_DIARIAS))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP VIEW IF EXISTS v_ventas_diarias"))
    metadata.drop_all(bind)
