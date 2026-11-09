"""
DukaanSaathi — Security & Access Control (Phase 9 Hardening)
Protects shopkeeper administrative APIs using cryptographically signed session tokens
with short-lived expiration, timing-safe verification, and store ownership validation.
"""

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from typing import Any, Dict, Optional, Set

from fastapi import Header, HTTPException, status
from backend.app.core.config import settings

# Thread-safe server-side revocation set for invalidated session tokens
_revoked_tokens: Set[str] = set()
_revocation_lock = threading.Lock()


def revoke_token(token: str) -> None:
    """Adds a token to the server-side revocation list upon logout."""
    if token:
        with _revocation_lock:
            _revoked_tokens.add(token)


def is_token_revoked(token: str) -> bool:
    """Checks if a session token has been revoked."""
    if not token:
        return True
    with _revocation_lock:
        return token in _revoked_tokens


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data_str: str) -> bytes:
    padding = "=" * ((4 - len(data_str) % 4) % 4)
    return base64.urlsafe_b64decode(data_str + padding)


def create_merchant_session_token(
    username: str,
    store_id: str,
    role: str = "merchant",
    expires_in: Optional[int] = None
) -> str:
    """
    Creates a cryptographically signed HMAC-SHA256 session token.
    Contains subject, store_id, issued-at (iat), and expiration (exp).
    """
    ttl = expires_in if expires_in is not None else settings.SESSION_EXPIRE_SECONDS
    now = int(time.time())
    payload = {
        "sub": username,
        "store_id": store_id,
        "role": role,
        "iat": now,
        "exp": now + ttl
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64encode(payload_json)

    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).digest()
    sig_b64 = _b64encode(signature)

    return f"{payload_b64}.{sig_b64}"


def verify_merchant_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies the cryptographic signature, revocation status, and expiration of a signed session token.
    Returns the decoded payload dict if valid, or None if invalid/expired/revoked.
    """
    if is_token_revoked(token):
        return None
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts[0], parts[1]

        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).digest()
        provided_sig = _b64decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        now = int(time.time())
        if payload.get("exp", 0) <= now:
            return None  # Expired

        return payload
    except Exception:
        return None


def verify_merchant_token(
    authorization: str = Header(None),
    x_merchant_token: str = Header(None)
) -> Dict[str, Any]:
    """
    Validates that incoming requests to administrative endpoints carry a valid merchant token.
    Accepts:
    1. Short-lived cryptographically signed session token.
    2. Master SHOPKEEPER_AUTH_TOKEN (verified via constant-time comparison for automated integration/CLI).
    """
    token = None
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            token = authorization

    if not token and x_merchant_token:
        token = x_merchant_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing merchant authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Check if token matches the configured server master token (timing-safe)
    if secrets.compare_digest(token, settings.SHOPKEEPER_AUTH_TOKEN):
        return {
            "sub": settings.MERCHANT_USERNAME,
            "store_id": settings.DEMO_STORE_ID,
            "role": "merchant",
            "type": "master"
        }

    # 2. Check signed session token
    session_data = verify_merchant_session_token(token)
    if session_data is not None:
        return session_data

    # Invalid or expired
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired merchant authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
