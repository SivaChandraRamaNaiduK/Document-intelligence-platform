"""
Application configuration.

Every setting is loaded from environment variables (or a .env file in dev).
Nothing sensitive is ever hardcoded. This module is imported everywhere via
`get_settings()`, which caches a single Settings instance.

POSTGRES_PASSWORD and JWT_SECRET_KEY have no defaults on purpose: the app
will refuse to start if .env doesn't supply them, rather than silently
falling back to a guessable value.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Document Intelligence Platform"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- Database ---
    POSTGRES_USER: str = "docintel"
    POSTGRES_PASSWORD: str          # required — must come from .env
    POSTGRES_DB: str = "docintel"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433

    # --- Auth (used from Week 2) ---
    JWT_SECRET_KEY: str             # required — must come from .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- LLM / embeddings (used from Week 4-5) ---
    LLM_PROVIDER: str = "cohere"    # cohere (embeddings + chat)
    COHERE_API_KEY: str = ""
    EMBEDDING_DIM: int = 1024        # embed-english-v3.0 output size
    # --- CORS ---
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        """Async URL for SQLAlchemy (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync URL used only by Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()