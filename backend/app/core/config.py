"""
DukaanSaathi — Application Configuration
Loads configuration from environment variables / .env.
"""

from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "DukaanSaathi API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./data/database/dukkaansaathi_seed.sqlite",
        description="Authoritative database connection string (PostgreSQL for production/Neon, SQLite for local dev)"
    )

    # Demo Store
    DEMO_STORE_ID: str = "STORE001"

    # Security & Signing (Phase 9)
    SECRET_KEY: str = Field(
        default="dukaansaathi-production-signing-secret-key-2026",
        description="Cryptographic HMAC signing secret for short-lived merchant session tokens"
    )
    SESSION_EXPIRE_SECONDS: int = 86400  # 24 hours
    ENABLE_HSTS: bool = False  # Enabled in production over HTTPS

    # Merchant Authentication
    SHOPKEEPER_AUTH_TOKEN: str = "demo-shopkeeper-secret-key-sharma-store"
    MERCHANT_USERNAME: str = Field(default="sharma", description="Default merchant login username")
    MERCHANT_PASSWORD: str = Field(default="kirana@2026", description="Default merchant login password")

    # CORS
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Gnani AI (Phase 1 verified)
    GNANI_API_KEY: Optional[str] = None
    GNANI_PRISMA_ENDPOINT: str = "https://api.vachana.ai/stt/v3"
    GNANI_TIMBRE_ENDPOINT: str = "https://api.vachana.ai/api/v1/tts/inference"


settings = Settings()
