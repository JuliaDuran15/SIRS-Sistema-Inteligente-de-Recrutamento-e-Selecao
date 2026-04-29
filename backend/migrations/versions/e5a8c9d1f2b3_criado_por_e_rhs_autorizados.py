"""criado_por_id e rhs_autorizados em vagas

Revision ID: e5a8c9d1f2b3
Revises: 313dfbc4f933
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = 'e5a8c9d1f2b3'
down_revision = '313dfbc4f933'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vagas', sa.Column('criado_por_id', UUID(as_uuid=True), nullable=True))
    op.add_column('vagas', sa.Column('rhs_autorizados', JSONB, nullable=True))


def downgrade():
    op.drop_column('vagas', 'rhs_autorizados')
    op.drop_column('vagas', 'criado_por_id')
