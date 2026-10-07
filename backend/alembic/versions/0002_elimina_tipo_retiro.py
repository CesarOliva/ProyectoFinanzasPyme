"""Elimina el tipo de gasto 'retiro': borra las filas y reduce el ENUM a fijo|variable.

Los retiros se eliminaron del modelo de negocio (oct 2026): un "Retiro personal"
en un archivo importado se clasifica como gasto variable. La migración borra las
filas existentes con tipo='retiro'; el downgrade restaura el ENUM pero no recupera
los datos borrados.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-07
"""

from alembic import op
from sqlalchemy import text

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DELETE FROM gastos_operativos WHERE tipo = 'retiro'"))
    op.alter_column(
        "gastos_operativos",
        "tipo",
        existing_type=text("ENUM('fijo','variable','retiro')"),
        type_=text("ENUM('fijo','variable')"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "gastos_operativos",
        "tipo",
        existing_type=text("ENUM('fijo','variable')"),
        type_=text("ENUM('fijo','variable','retiro')"),
        existing_nullable=False,
    )