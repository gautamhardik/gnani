import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.app.core.config import settings
from backend.app.core.database import get_db, get_database_url
from backend.app.main import app

# Ensure PostgreSQL connection URL
PG_URL = get_database_url()

@pytest.fixture(scope="session")
def pg_engine():
    """Authoritative real PostgreSQL 16.6 engine."""
    engine = create_engine(PG_URL, pool_pre_ping=True)
    # Verify live connection
    with engine.connect() as conn:
        pass
    yield engine
    engine.dispose()

@pytest.fixture(scope="session")
def pg_session_factory(pg_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

@pytest.fixture(scope="function")
def pg_db(pg_session_factory):
    """Provides a transactional database session against real PostgreSQL."""
    session: Session = pg_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def pg_client(pg_session_factory):
    """FastAPI TestClient wired to real PostgreSQL."""
    def override_get_db():
        session = pg_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def pg_merchant_headers(pg_client):
    """Obtains authentic merchant JWT/Bearer token via login endpoint."""
    login_resp = pg_client.post("/api/v1/auth/login", json={
        "username": settings.MERCHANT_USERNAME,
        "password": settings.MERCHANT_PASSWORD
    })
    token = login_resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
