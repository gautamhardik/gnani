"""
DukaanSaathi — Database Engine and Session Management
Supports PostgreSQL (Production/Neon) with automatic local SQLite fallback
if local PostgreSQL daemon is not running.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

logger = logging.getLogger("dukaansaathi.database")

def get_engine():
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(url, connect_args=connect_args)

    # For PostgreSQL, verify if connection succeeds; if localhost fails, fallback to SQLite
    try:
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            pass
        return eng
    except Exception as e:
        if "localhost" in url or "127.0.0.1" in url:
            fallback_url = "sqlite:///./data/database/dukkaansaathi_dev.sqlite"
            logger.warning(
                f"[DATABASE WARNING] Local PostgreSQL ({url}) connection failed: {e}. "
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
