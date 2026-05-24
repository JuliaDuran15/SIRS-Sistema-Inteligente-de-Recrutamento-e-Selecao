"""Reverte vetores de 768 para 384 dimensões.

O .env usa paraphrase-multilingual-MiniLM-L12-v2 (384d), mas a migração
d7e2f3a1b8c0 havia alterado as colunas para 768d. Esta migração sincroniza
o banco com o modelo em uso.

Revision ID: a1b2c3d4e5f6
Revises: f3c1d2e4a5b6
Create Date: 2026-05-17

"""
from alembic import op
from pgvector.sqlalchemy import Vector

revision = 'a1b2c3d4e5f6'
down_revision = 'f3c1d2e4a5b6'
branch_labels = None
depends_on = None

OLD_DIM = 768
NEW_DIM = 384


def upgrade():
    op.alter_column('curriculos', 'vetor_embedding',
        type_=Vector(NEW_DIM), postgresql_using='NULL')
    op.alter_column('curriculos', 'vetor_secao_exp',
        type_=Vector(NEW_DIM), postgresql_using='NULL')
    op.alter_column('curriculos', 'vetor_secao_skills',
        type_=Vector(NEW_DIM), postgresql_using='NULL')

    op.alter_column('vagas', 'vetor_vaga',
        type_=Vector(NEW_DIM), postgresql_using='NULL')
    op.alter_column('vagas', 'vetor_mercado',
        type_=Vector(NEW_DIM), postgresql_using='NULL')


def downgrade():
    op.alter_column('curriculos', 'vetor_embedding',
        type_=Vector(OLD_DIM), postgresql_using='NULL')
    op.alter_column('curriculos', 'vetor_secao_exp',
        type_=Vector(OLD_DIM), postgresql_using='NULL')
    op.alter_column('curriculos', 'vetor_secao_skills',
        type_=Vector(OLD_DIM), postgresql_using='NULL')

    op.alter_column('vagas', 'vetor_vaga',
        type_=Vector(OLD_DIM), postgresql_using='NULL')
    op.alter_column('vagas', 'vetor_mercado',
        type_=Vector(OLD_DIM), postgresql_using='NULL')
