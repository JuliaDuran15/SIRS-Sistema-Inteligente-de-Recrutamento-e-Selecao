"""Adiciona vetores de seção ao currículo (exp, skills).

Também inclui instruções comentadas para quem quiser trocar o modelo de
embedding para 768d (all-mpnet-base-v2 ou similar).

Revision ID: c4b7a2d8e1f9
Revises: f3c1d2e4a5b6
Create Date: 2026-04-29

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = 'c4b7a2d8e1f9'
down_revision = 'f3c1d2e4a5b6'
branch_labels = None
depends_on = None

# Dimensão padrão (mude se alterou EMBEDDING_DIM no .env)
DIM = 384


def upgrade():
    # ── Vetores de seção (currículo) ─────────────────────────────────────────
    op.add_column('curriculos', sa.Column('vetor_secao_exp',    Vector(DIM), nullable=True))
    op.add_column('curriculos', sa.Column('vetor_secao_skills', Vector(DIM), nullable=True))

    # ── Para trocar de 384 → 768 dims, descomente e ajuste DIM acima ─────────
    # op.alter_column('curriculos', 'vetor_embedding',
    #     type_=Vector(DIM), postgresql_using='NULL')
    # op.alter_column('vagas', 'vetor_vaga',
    #     type_=Vector(DIM), postgresql_using='NULL')
    # op.alter_column('vagas', 'vetor_mercado',
    #     type_=Vector(DIM), postgresql_using='NULL')
    # Após rodar a migração, reprocesse todos os currículos e vagas:
    #   docker compose exec api python scripts/reprocessar_tudo.py


def downgrade():
    op.drop_column('curriculos', 'vetor_secao_skills')
    op.drop_column('curriculos', 'vetor_secao_exp')
