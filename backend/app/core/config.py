"""
Application configuration settings.
"""

from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "Dealership AI Parts System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # MFA Settings
    MFA_ISSUER_NAME: str = "Dealership Parts System"
    MFA_BACKUP_CODES_COUNT: int = 10

    # Password Policy
    MIN_PASSWORD_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 30

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "dealership_parts"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    # AI/LLM
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "dealership-parts-system"
    LLM_PRIMARY_MODEL: str = "claude-sonnet-4-20250514"
    LLM_FALLBACK_MODEL: str = "gpt-4.1-mini"

    # Email
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_USE_TLS: bool = True

    # IMAP
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""

    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""

    # Shipping
    EASYPOST_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            if v.strip().startswith("["):
                import json

                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Web Scraping
    PLAYWRIGHT_BROWSER_WS_ENDPOINT: Optional[str] = None
    SCRAPY_USER_AGENT: str = "DealershipPartsBot/1.0"

    # Rate Limiting
    EMAIL_PROCESSING_INTERVAL: int = 30  # seconds
    MAX_EMAILS_PER_BATCH: int = 10
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120
    RATE_LIMIT_PER_HOUR: int = 2000

    # Auth — AUTH_MODE=demo|production (see app.api.deps.require_user_if_production)
    # demo: mutating routes open without Bearer; production: JWT required
    AUTH_MODE: str = "demo"

    # Vector / pgvector production path
    # When True and Postgres reachable with vector extension, prefer pgvector search.
    # Offline demos keep parrts core (FAISS/numpy) regardless.
    PGVECTOR_ENABLED: bool = False
    VECTOR_BACKEND: str = "auto"  # auto | parrts | pgvector
    PGVECTOR_HNSW: bool = True
    EMBEDDING_DIM: int = 1536


# Global settings instance
settings = Settings()
