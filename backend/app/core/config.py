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