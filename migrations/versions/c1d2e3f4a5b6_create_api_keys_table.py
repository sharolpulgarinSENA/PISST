"""create_api_keys_table

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-06-10 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table in inspector.get_table_names()


def upgrade() -> None:
    if _table_exists("api_keys"):
        return
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clave", sa.String(length=70), nullable=False),
        sa.Column("descripcion", sa.String(length=200), nullable=True),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            name="api_keys_empresa_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_clave", "api_keys", ["clave"], unique=True)


def downgrade() -> None:
    if not _table_exists("api_keys"):
        return
    op.drop_index("ix_api_keys_clave", table_name="api_keys")
    op.drop_table("api_keys")
