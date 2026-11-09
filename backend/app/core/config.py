"""
DukaanSaathi — Application Configuration
Loads configuration from environment variables / .env.
"""

from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator


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
    DATABASE_POOL_SIZE: int = 15
    DATABASE_MAX_OVERFLOW: int = 25
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

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

    @model_validator(mode="after")
    def validate_production_environment(self) -> "Settings":
        """
        Fail fast with actionable error if required staging/production secrets
        are missing, blank, or using insecure default/placeholder values.
        """
        if self.APP_ENV.lower() in ("staging", "production"):
            errors: List[str] = []

            # Database: SQLite is strictly forbidden in staging/production
            if not self.DATABASE_URL or not (
                self.DATABASE_URL.startswith("postgresql://") or self.DATABASE_URL.startswith("postgres://")
            ):
                errors.append(
                    "DATABASE_URL must be an authoritative PostgreSQL connection string (postgresql://...) "
                    "in staging/production environments. SQLite fallback is strictly prohibited."
                )

            # Cryptographic Signing Secret
            insecure_secret_defaults = {
                "dukaansaathi-production-signing-secret-key-2026",
                "secret",
                "changeme",
                "password",
                "default",
            }
            if not self.SECRET_KEY or self.SECRET_KEY in insecure_secret_defaults or len(self.SECRET_KEY) < 32:
                errors.append(
                    "SECRET_KEY must be a secure, non-default cryptographic secret of at least 32 characters "
                    "in staging/production environments."
                )

            # Merchant Authentication Token
            insecure_auth_defaults = {
                "demo-shopkeeper-secret-key-sharma-store",
                "demo",
                "changeme",
                "admin",
            }
            if not self.SHOPKEEPER_AUTH_TOKEN or self.SHOPKEEPER_AUTH_TOKEN in insecure_auth_defaults or len(self.SHOPKEEPER_AUTH_TOKEN) < 16:
                errors.append(
                    "SHOPKEEPER_AUTH_TOKEN must be configured with a secure, non-default bearer secret "
                    "of at least 16 characters in staging/production environments."
                )

            # Gnani AI API Key
            insecure_gnani_keys = {"mock", "placeholder", "test", "demo"}
            if not self.GNANI_API_KEY or self.GNANI_API_KEY.lower() in insecure_gnani_keys:
                errors.append(
                    "GNANI_API_KEY must be populated with a valid Gnani production API key in staging/production environments."
                )

            if errors:
                error_msg = (
                    f"\n[FATAL STARTUP CONFIGURATION ERROR] Environment '{self.APP_ENV}' failed validation:\n"
                    + "\n".join(f"  - {err}" for err in errors)
                )
                raise ValueError(error_msg)

        return self


settings = Settings()
