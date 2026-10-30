"""
DukaanSaathi — Stores API Tests
"""

import pytest

def test_get_demo_store(client):
    """Verifies fetching store profile, hours, and status."""
    resp = client.get("/api/v1/stores/STORE001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["store_id"] == "STORE001"
    assert "Sharma General Store" in data["store_name"]
    assert data["is_open"] is True
    assert "hi-IN" in data["supported_languages"]
    assert "currency" in data

def test_get_unknown_store(client):
    """Verifies 404 for unknown store."""
    resp = client.get("/api/v1/stores/STORE_DOES_NOT_EXIST")
    assert resp.status_code == 404
