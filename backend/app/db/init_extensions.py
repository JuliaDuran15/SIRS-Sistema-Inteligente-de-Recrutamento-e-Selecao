from sqlalchemy import text
from app.db.session import engine

def criar_extensoes():
    """
    Ativa a extensão pgvector no PostgreSQL.
    Precisa rodar uma vez antes das migrações.
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()