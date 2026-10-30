import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.scripts.seed_db import seed_database

# Create isolated in-memory test database with StaticPool to share connection across sessions
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session")
def setup_test_db():
    """Builds schema and loads starter pack into isolated in-memory test database."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        seed_database(db, bind_engine=test_engine)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def db_session(setup_test_db):
    """Provides a transactional database session per test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client(setup_test_db):
    """TestClient wired to the test database session."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def merchant_headers():
    return {
        "Authorization": f"Bearer {settings.SHOPKEEPER_AUTH_TOKEN}"
    }

