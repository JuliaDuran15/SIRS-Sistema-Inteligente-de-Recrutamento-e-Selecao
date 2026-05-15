"""Altera vetores de embedding de 384 para 768 dimensões.

Necessário ao trocar EMBEDDING_MODEL para paraphrase-multilingual-mpnet-base-v2.
Zera os vetores existentes (incompatíveis entre dimensões) — após rodar,
execute reprocessar_todos_curriculos e re-salve as vagas para regeração dos vetores.

Revision ID: d7e2f3a1b8c0
Revises: ccee08033715
Create Date: 2026-05-13

"""
from alembic import op
from pgvector.sqlalchemy import Vector

revision = 'd7e2f3a1b8c0'
down_revision = 'ccee08033715'
branch_labels = None
depends_on = None

OLD_DIM = 384
NEW_DIM = 768


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
