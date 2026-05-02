from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ENVIRONMENT: str = "development"

    ADMIN_EMAIL : str = "admin@sirs.com"
    ADMIN_SENHA : str = "admin123"


    ADZUNA_APP_ID          : str = ""
    ADZUNA_APP_KEY         : str = ""
    ADZUNA_COUNTRY         : str = "br"
    MARKET_ANALYZER_SOURCE : str = "adzuna"

    # ── Modelos de embedding e reranking ──────────────────────────────────────
    # Troca de modelo exige: 1) reiniciar containers  2) rodar migração para
    # alterar dimensão dos vetores  3) reprocessar todos os currículos/vagas.
    EMBEDDING_MODEL : str = "all-MiniLM-L6-v2"   # ou "all-mpnet-base-v2" (768d)
    EMBEDDING_DIM   : int = 384                    # mude junto com o modelo
    RERANKER_MODEL  : str = "BAAI/bge-reranker-base"
    RERANKER_TOP_N  : int = 20                     # quantos candidatos reordenar

    # Webhook — deixe vazio para desabilitar autenticação (dev)
    WEBHOOK_SECRET_KEY : str = ""

    # SMTP — deixe vazio para desabilitar envio de e-mail
    SMTP_HOST    : str = ""
    SMTP_PORT    : int = 587
    SMTP_USER    : str = ""
    SMTP_PASS    : str = ""
    SMTP_FROM    : str = ""
    FRONTEND_URL : str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()