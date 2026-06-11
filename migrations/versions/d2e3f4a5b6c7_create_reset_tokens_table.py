"""create_reset_tokens_table

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-10 12:01:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=70), nullable=False),
        sa.Column("usado", sa.Boolean(), nullable=False),
        sa.Column("expira_en", sa.DateTime(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["users.id"],
            name="reset_tokens_usuario_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reset_tokens_token", "reset_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_reset_tokens_token", table_name="reset_tokens")
    op.drop_table("reset_tokens")
