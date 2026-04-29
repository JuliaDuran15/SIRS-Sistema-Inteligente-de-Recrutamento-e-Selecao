"""Move origem/fonte de candidatos para candidaturas

Revision ID: f3c1d2e4a5b6
Revises: e5a8c9d1f2b3
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa

revision = 'f3c1d2e4a5b6'
down_revision = 'e5a8c9d1f2b3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('candidaturas', sa.Column('origem', sa.String(30), nullable=False, server_default='manual'))
    op.add_column('candidaturas', sa.Column('fonte',  sa.String(100), nullable=True))
    op.drop_column('candidatos', 'origem')
    op.drop_column('candidatos', 'fonte')


def downgrade():
    op.add_column('candidatos', sa.Column('fonte',  sa.String(100), nullable=True))
    op.add_column('candidatos', sa.Column('origem', sa.String(30),  nullable=False, server_default='manual'))
    op.drop_column('candidaturas', 'fonte')
    op.drop_column('candidaturas', 'origem')
