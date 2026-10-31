"""
DukaanSaathi — Phase 10 Production Configuration & Deployment Tests
Verifies fail-fast startup validation for staging and production environments.
"""

import pytest
from backend.app.core.config import Settings


def test_development_environment_allows_local_defaults():
    """Development environment must allow default SQLite, placeholder secrets, and mock Gnani."""
    config = Settings(
        APP_ENV="development",
        DATABASE_URL="sqlite:///./data/database/dukkaansaathi_seed.sqlite",
        SECRET_KEY="dukaansaathi-production-signing-secret-key-2026",
        SHOPKEEPER_AUTH_TOKEN="demo-shopkeeper-secret-key-sharma-store",
        GNANI_API_KEY=None,
    )
    assert config.APP_ENV == "development"
    assert config.DATABASE_URL.startswith("sqlite")


def test_production_environment_rejects_default_and_insecure_settings():
    """Staging and production must reject SQLite, default secrets, and missing Gnani keys."""
    with pytest.raises(ValueError) as excinfo:
        Settings(
            APP_ENV="production",
            DATABASE_URL="sqlite:///./data/database/dukkaansaathi_seed.sqlite",
            SECRET_KEY="dukaansaathi-production-signing-secret-key-2026",
            SHOPKEEPER_AUTH_TOKEN="demo-shopkeeper-secret-key-sharma-store",
            GNANI_API_KEY=None,
        )

    error_text = str(excinfo.value)
    assert "DATABASE_URL must be an authoritative PostgreSQL connection string" in error_text
    assert "SECRET_KEY must be a secure, non-default cryptographic secret" in error_text
    assert "SHOPKEEPER_AUTH_TOKEN must be configured with a secure, non-default bearer secret" in error_text
    assert "GNANI_API_KEY must be populated" in error_text


def test_staging_environment_rejects_mock_gnani_key():
    """Staging must reject 'mock' or 'test' placeholder API keys."""
    with pytest.raises(ValueError) as excinfo:
        Settings(
            APP_ENV="staging",
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dukaansaathi_staging",
            SECRET_KEY="super-secret-random-hex-string-for-phase-10-production-signing-key",
            SHOPKEEPER_AUTH_TOKEN="merchant-super-secure-token-123456",
            GNANI_API_KEY="mock",
        )

    error_text = str(excinfo.value)
    assert "GNANI_API_KEY must be populated with a valid Gnani production API key" in error_text


def test_production_environment_accepts_valid_configuration():
    """Production must succeed when all authoritative secrets and PostgreSQL connection strings are provided."""
    config = Settings(
        APP_ENV="production",
        DATABASE_URL="postgresql://neondb_owner:npg_secret123@ep-proud-water-12345.ap-southeast-1.neon.tech/neondb?sslmode=require",
        SECRET_KEY="e8f498c19a0d24bf5f98e6a12b9c7481f3d82046b9a4c8710352ef61a0984c37",
        SHOPKEEPER_AUTH_TOKEN="prod-sharma-store-auth-token-998822",
        GNANI_API_KEY="gnani_live_production_key_sample_88339",
    )
    assert config.APP_ENV == "production"
    assert config.DATABASE_URL.startswith("postgresql://")
    assert len(config.SECRET_KEY) >= 32

