"""
DukaanSaathi — Phase 9 Security Hardening & Vulnerability Regression Suite
Verifies:
1. Authentication bypass protection on all administrative routes.
2. Expired and tampered cryptographic session token rejection.
3. Order enumeration prevention (requires merchant auth or matching customer session).
4. Store isolation and unauthorized cross-store access prevention.
5. Defensive security headers (CSP, nosniff, frame-ancestors, permissions-policy).
6. Rate limiting enforcement on sensitive endpoints.
7. Path traversal prevention on audio identifier routes.
8. Error disclosure sanitization in health checks and database exceptions.
9. Secret scanning verification across environment examples and frontend bundles.
"""

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.rate_limiter import limiter
from backend.app.core.security import create_merchant_session_token, verify_merchant_session_token


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state before each test to ensure test isolation."""
    limiter.reset()
    yield
    limiter.reset()


# ---------------------------------------------------------------------------
# 1. Authentication Bypass Protection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/merchant/overview"),
    ("GET", "/api/v1/orders"),
    ("POST", "/api/v1/orders/ORD_TEST/accept"),
    ("POST", "/api/v1/orders/ORD_TEST/reject"),
    ("POST", "/api/v1/orders/ORD_TEST/status"),
    ("GET", "/api/v1/inventory/movements"),
    ("PUT", "/api/v1/inventory/PRD001"),
    ("POST", "/api/v1/products"),
    ("PUT", "/api/v1/products/PRD001"),
    ("DELETE", "/api/v1/products/PRD001"),
])
def test_merchant_endpoints_reject_unauthenticated_requests(client, method, path):
    """Verifies that all administrative endpoints strictly reject unauthenticated calls with 401."""
    if method == "GET":
        resp = client.get(path)
    elif method == "POST":
        resp = client.post(path, json={})
    elif method == "PUT":
        resp = client.put(path, json={})
    elif method == "DELETE":
        resp = client.delete(path)
    else:
        pytest.fail(f"Unsupported method {method}")

    assert resp.status_code == 401, f"Endpoint {method} {path} returned {resp.status_code}, expected 401"
    assert "WWW-Authenticate" in resp.headers


def test_expired_session_token_rejected_with_401(client):
    """Verifies that short-lived session tokens are rejected once expired."""
    # Create an expired token (expired 10 seconds ago)
    expired_token = create_merchant_session_token(
        username=settings.MERCHANT_USERNAME,
        store_id=settings.DEMO_STORE_ID,
        expires_in=-10
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401
    assert "Invalid or expired" in resp.json()["detail"]


def test_tampered_session_token_rejected_with_401(client):
    """Verifies that forged or modified token signatures are rejected."""
    valid_token = create_merchant_session_token(
        username=settings.MERCHANT_USERNAME,
        store_id=settings.DEMO_STORE_ID,
        expires_in=3600
    )
    payload_b64, sig_b64 = valid_token.split(".")

    # Tamper payload
    tampered_payload_json = json.dumps({
        "sub": "attacker",
        "store_id": settings.DEMO_STORE_ID,
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time() + 3600)
    }).encode("utf-8")
    tampered_b64 = base64.urlsafe_b64encode(tampered_payload_json).decode("utf-8").rstrip("=")

    forged_token = f"{tampered_b64}.{sig_b64}"
    headers = {"Authorization": f"Bearer {forged_token}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Authorization & Order Enumeration Protection
# ---------------------------------------------------------------------------

def test_order_details_requires_authorization(client):
    """
    Verifies that GET /api/v1/orders/{order_id} cannot be enumerated by anonymous callers.
    Requires either merchant authorization or customer session ownership.
    """
    # 1. Place an order as a customer
    sess_resp = client.post("/api/v1/sessions", json={"store_id": settings.DEMO_STORE_ID})
    session_id = sess_resp.json()["session_id"]

    order_resp = client.post("/api/v1/orders", json={
        "store_id": settings.DEMO_STORE_ID,
        "session_id": session_id,
        "items": [{"product_id": "PRD001", "quantity": 1.0}]
    })
    order_id = order_resp.json()["order_id"]

    # 2. Anonymous request without auth or session_id must be rejected
    anon_resp = client.get(f"/api/v1/orders/{order_id}")
    assert anon_resp.status_code == 401
    assert "Authentication required" in anon_resp.json()["detail"]

    # 3. Request with wrong customer session_id must be rejected
    wrong_sess_resp = client.get(f"/api/v1/orders/{order_id}?session_id=SESS_WRONG_999")
    assert wrong_sess_resp.status_code == 401

    # 4. Request with matching customer session_id succeeds
    owner_resp = client.get(f"/api/v1/orders/{order_id}?session_id={session_id}")
    assert owner_resp.status_code == 200
    assert owner_resp.json()["order_id"] == order_id

    # 5. Request with merchant authorization succeeds
    merchant_resp = client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {settings.SHOPKEEPER_AUTH_TOKEN}"}
    )
    assert merchant_resp.status_code == 200
    assert merchant_resp.json()["order_id"] == order_id


def test_merchant_cross_store_access_forbidden(client):
    """
    Verifies that a merchant token bound to STORE_OTHER cannot access STORE001.
    """
    other_store_token = create_merchant_session_token(
        username="other_merchant",
        store_id="STORE_OTHER_999",
        expires_in=3600
    )
    headers = {"Authorization": f"Bearer {other_store_token}"}

    # Cannot view overview of STORE001
    resp = client.get(f"/api/v1/merchant/overview?store_id={settings.DEMO_STORE_ID}", headers=headers)
    assert resp.status_code == 403
    assert "Unauthorized" in resp.json()["detail"]

    # Cannot list orders of STORE001
    resp = client.get(f"/api/v1/orders?store_id={settings.DEMO_STORE_ID}", headers=headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3. Defensive Security Headers
# ---------------------------------------------------------------------------

def test_defensive_security_headers_present(client):
    """Verifies that all standard defensive HTTP headers are attached to responses."""
    resp = client.get("/")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "microphone=(self)" in headers.get("Permissions-Policy", "")
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in headers.get("Content-Security-Policy", "")


# ---------------------------------------------------------------------------
# 4. Rate Limiting Protection
# ---------------------------------------------------------------------------

def test_login_rate_limiting_enforced(client):
    """Verifies that brute-force login attempts trigger HTTP 429 Too Many Requests."""
    for i in range(10):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "sharma", "password": "wrong_password"}
        )
        assert resp.status_code == 401

    # 11th request must be blocked by rate limiter
    exceeded_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "sharma", "password": "wrong_password"}
    )
    assert exceeded_resp.status_code == 429
    assert "Rate limit exceeded" in exceeded_resp.json()["detail"]
    assert "Retry-After" in exceeded_resp.headers


# ---------------------------------------------------------------------------
# 5. Audio Identifier Path Traversal Guard
# ---------------------------------------------------------------------------

def test_audio_endpoint_rejects_path_traversal(client):
    """Verifies that /audio/{audio_id} rejects malicious path traversal sequences."""
    traversal_ids = [
        "../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "aud_<script>alert(1)</script>",
        "aud;DROP TABLE users;--",
        "a",  # too short (< 4 chars)
    ]
    for bad_id in traversal_ids:
        resp = client.get(f"/api/v1/voice/audio/{bad_id}")
        assert resp.status_code in (400, 404), f"Path {bad_id} returned {resp.status_code}"


# ---------------------------------------------------------------------------
# 6. Health & Error Disclosure Sanitization
# ---------------------------------------------------------------------------

def test_health_check_sanitization(client):
    """
    Verifies that /health, /health/live, and /health/ready provide operational status
    without exposing database passwords, hostnames, or internal stack traces.
    """
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "initializing")
    assert data["database_connected"] is True
    # Verify no passwords or connection strings leaked
    data_str = json.dumps(data)
    assert "password" not in data_str.lower()
    assert "postgresql://" not in data_str
    assert "sqlite:///" not in data_str

    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "alive"

    ready_resp = client.get("/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"


# ---------------------------------------------------------------------------
# 7. Secret Scanning Verification
# ---------------------------------------------------------------------------

def test_no_actual_secrets_in_tracked_env_or_frontend():
    """
    Scans environment example files, frontend codebase, and configuration
    to verify no actual API keys, server tokens, or private secrets are tracked.
    """
    root_dir = Path(__file__).resolve().parents[2]

    # Check .env.example files
    backend_env_example = root_dir / ".env.example"
    assert backend_env_example.exists()
    content = backend_env_example.read_text(encoding="utf-8")
    assert "your_gnani_api_key_here" in content

    # Scan all frontend source files for accidental secret exposure
    frontend_dir = root_dir / "frontend"
    for ts_file in frontend_dir.glob("**/*.ts*"):
        if "node_modules" in str(ts_file) or ".next" in str(ts_file):
            continue
        text = ts_file.read_text(encoding="utf-8")
        assert "GNANI_API_KEY" not in text
        assert "SHOPKEEPER_AUTH_TOKEN" not in text
