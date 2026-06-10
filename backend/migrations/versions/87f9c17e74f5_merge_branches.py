"""merge branches

Revision ID: 87f9c17e74f5
Revises: a1b2c3d4e5f6, d7e2f3a1b8c0
Create Date: 2026-05-17 22:40:55.809568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87f9c17e74f5'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'd7e2f3a1b8c0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
