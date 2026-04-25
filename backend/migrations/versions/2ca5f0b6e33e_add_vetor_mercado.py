"""add_vetor_mercado

Revision ID: 2ca5f0b6e33e
Revises: 2836c5d9c56c
Create Date: 2026-04-12 23:09:36.598686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ca5f0b6e33e'
down_revision: Union[str, None] = '2836c5d9c56c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.execute("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS vetor_mercado vector(384)")


def downgrade() -> None:
    op.execute("ALTER TABLE vagas DROP COLUMN IF EXISTS vetor_mercado")