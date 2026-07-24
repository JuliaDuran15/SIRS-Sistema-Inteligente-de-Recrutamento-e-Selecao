"""add_links_to_candidato

Revision ID: b1e4f2a9c7d0
Revises: 3bc0ee98b2af
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1e4f2a9c7d0'
down_revision: Union[str, None] = '3bc0ee98b2af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('candidatos', sa.Column('linkedin_url', sa.String(300), nullable=True))
    op.add_column('candidatos', sa.Column('portfolio_url', sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column('candidatos', 'portfolio_url')
    op.drop_column('candidatos', 'linkedin_url')
