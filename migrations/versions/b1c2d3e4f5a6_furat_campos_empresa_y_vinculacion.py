"""furat_campos_empresa_y_vinculacion

Revision ID: b1c2d3e4f5a6
Revises: 4b8c830edc2c
Create Date: 2026-06-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "4b8c830edc2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("empresas", sa.Column("ciudad", sa.String(100), nullable=True))
    op.add_column("empresas", sa.Column("direccion", sa.String(300), nullable=True))
    op.add_column("empresas", sa.Column("telefono", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("tipo_vinculacion", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("empresas", "ciudad")
    op.drop_column("empresas", "direccion")
    op.drop_column("empresas", "telefono")
    op.drop_column("users", "tipo_vinculacion")
