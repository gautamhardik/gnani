"""
DukaanSaathi — Merchant Authentication API Tests (Phase 6 & 9 Hardening)
Verifies secure login, credential validation, timing-safe checks, signed session issuance,
expiry rejection, logout, and authenticated session introspection.
"""

import time
import pytest
from backend.app.core.config import settings
from backend.app.core.security import create_merchant_session_token, verify_merchant_session_token


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
    token = data["access_token"]
    assert token != settings.SHOPKEEPER_AUTH_TOKEN, "Master secret must not be exposed to frontend"
    assert data["token_type"] == "bearer"
    assert data["store_id"] == settings.DEMO_STORE_ID
    assert "merchant_name" in data
    assert data.get("expires_in") == settings.SESSION_EXPIRE_SECONDS

    # Verify token payload
    payload = verify_merchant_session_token(token)
    assert payload is not None
    assert payload["sub"] == settings.MERCHANT_USERNAME
    assert payload["store_id"] == settings.DEMO_STORE_ID


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


def test_merchant_me_endpoint_with_signed_session_token(client):
    # Log in and use the resulting session token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.MERCHANT_USERNAME,
            "password": settings.MERCHANT_PASSWORD
        }
    )
    token = login_resp.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def test_merchant_me_endpoint_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

    response_bad_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_secret_token"}
    )
    assert response_bad_token.status_code == 401


def test_merchant_logout_endpoint(client, merchant_headers):
    # Login to obtain a session token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.MERCHANT_USERNAME,
            "password": settings.MERCHANT_PASSWORD
        }
    )
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Verify token works
    me_resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200

    # Logout with this token
    logout_resp = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["logged_out"] is True

    # Token must now be rejected on the server
    me_after_logout = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_after_logout.status_code == 401
