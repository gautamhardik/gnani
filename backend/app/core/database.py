"""
DukaanSaathi — Database Engine and Session Management
Supports PostgreSQL (Production/Neon) with automatic local SQLite fallback
if local PostgreSQL daemon is not running.
"""

import logging
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

logger = logging.getLogger("dukaansaathi.database")


def sanitize_db_url(url: str) -> str:
    """
    Masks user credentials in database connection strings
    to prevent password disclosure in logs, exceptions, and monitoring feeds.
    """
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:******@", url)


def get_database_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_engine():
    url = get_database_url()
    safe_url = sanitize_db_url(url)

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(url, connect_args=connect_args)

    # For PostgreSQL, verify if connection succeeds; in staging/production, fail loudly
    try:
        eng = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
        )
        with eng.connect() as conn:
            pass
        return eng
    except Exception as e:
        if settings.APP_ENV.lower() in ("staging", "production"):
            logger.error(
                f"[DATABASE ERROR] Critical: Cannot connect to PostgreSQL in {settings.APP_ENV} environment: {type(e).__name__}. "
                "Silent fallback to SQLite is strictly disabled in staging/production."
            )
            raise RuntimeError(
                f"Database connection to '{safe_url}' failed in {settings.APP_ENV} environment. "
                "Silent SQLite fallback is strictly disabled in staging and production."
            ) from e

        if "localhost" in url or "127.0.0.1" in url:
            fallback_url = "sqlite:///./data/database/dukkaansaathi_dev.sqlite"
            logger.warning(
                f"[DATABASE WARNING] Local PostgreSQL ({safe_url}) connection failed: {type(e).__name__}. "
                f"Falling back to local SQLite: {fallback_url}"
            )
            print(f"[INFO] Local PostgreSQL unavailable on localhost; using SQLite fallback: {fallback_url}")
            return create_engine(fallback_url, connect_args={"check_same_thread": False})
        raise e

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency yielding database sessions."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
