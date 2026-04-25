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

    class Config:
        env_file = ".env"

settings = Settings()