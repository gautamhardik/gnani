"""
DukaanSaathi — Merchant Authentication API Tests (Phase 6)
Verifies secure login, credential validation, and authenticated session introspection.
"""

import pytest
from backend.app.core.config import settings


def test_merchant_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.MERCHANT_USERNAME,
            "password": settings.MERCHANT_PASSWORD
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == settings.SHOPKEEPER_AUTH_TOKEN
    assert data["token_type"] == "bearer"
    assert data["store_id"] == settings.DEMO_STORE_ID
    assert "merchant_name" in data


def test_merchant_login_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.MERCHANT_USERNAME,
            "password": "wrong_password_123"
        }
    )
    assert response.status_code == 401
    assert "Galat" in response.json()["detail"]


def test_merchant_login_invalid_username(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "unknown_admin",
            "password": settings.MERCHANT_PASSWORD
        }
    )
    assert response.status_code == 401


def test_merchant_me_endpoint_with_valid_token(client, merchant_headers):
    response = client.get("/api/v1/auth/me", headers=merchant_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["store_id"] == settings.DEMO_STORE_ID


def test_merchant_me_endpoint_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

    response_bad_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_secret_token"}
    )
    assert response_bad_token.status_code == 401
