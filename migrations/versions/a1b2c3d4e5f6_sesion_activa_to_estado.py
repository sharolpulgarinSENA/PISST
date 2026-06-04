"""feat: reemplazar activa por estado en sesiones_capacitacion

Revision ID: a1b2c3d4e5f6
Revises: 63a28ad36845
Create Date: 2026-06-04 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "63a28ad36845"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar columna estado con default "programada"
    op.add_column(
        "sesiones_capacitacion",
        sa.Column("estado", sa.String(20), nullable=False, server_default="programada"),
    )

    # 2. Migrar datos existentes
    op.execute(
        """
        UPDATE sesiones_capacitacion
        SET estado = CASE
            WHEN activa = TRUE  THEN 'programada'
            WHEN activa = FALSE THEN 'cancelada'
            ELSE 'programada'
        END
        """
    )

    # 3. Eliminar columna antigua
    op.drop_column("sesiones_capacitacion", "activa")


def downgrade() -> None:
    op.add_column(
        "sesiones_capacitacion",
        sa.Column("activa", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.execute(
        """
        UPDATE sesiones_capacitacion
        SET activa = CASE
            WHEN estado = 'cancelada' THEN FALSE
            ELSE TRUE
        END
        """
    )

    op.drop_column("sesiones_capacitacion", "estado")
