"""
DukaanSaathi — Merchant Authentication Router (Phase 9 Hardening)
Provides secure backend-mediated login, constant-time credential comparison,
short-lived signed session issuance, brute-force rate limiting, and session logout.
"""

import secrets
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_current_merchant
from backend.app.core.config import settings
from backend.app.core.rate_limiter import enforce_rate_limit
from backend.app.core.security import create_merchant_session_token, revoke_token
from backend.app.models import Store
from backend.app.schemas.auth import (
    MerchantLoginRequest,
    MerchantLoginResponse,
    MerchantMeResponse,
    MerchantLogoutResponse,
)

router = APIRouter(prefix="/auth", tags=["Merchant Authentication"])


@router.post("/login", response_model=MerchantLoginResponse)
def merchant_login(
    login_in: MerchantLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("login", max_requests=10, window_seconds=60))
):
    """
    Authenticates shopkeeper credentials using timing-safe comparison,
    and returns a short-lived cryptographically signed session bearer token.
    Sets secure HttpOnly cookie and enforces brute-force rate limits (max 10 attempts per minute per IP).
    """
    is_valid_user = secrets.compare_digest(login_in.username, settings.MERCHANT_USERNAME)
    is_valid_pass = secrets.compare_digest(login_in.password, settings.MERCHANT_PASSWORD)

    if not (is_valid_user and is_valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Galat username ya password. Kripya sahi credentials daalein.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    store = db.query(Store).filter(Store.store_id == settings.DEMO_STORE_ID).first()
    store_name = store.store_name if store else "Everyday Needs General Store"

    # Issue short-lived cryptographically signed session token
    signed_token = create_merchant_session_token(
        username=login_in.username,
        store_id=settings.DEMO_STORE_ID,
        role="merchant",
        expires_in=settings.SESSION_EXPIRE_SECONDS
    )

    # Set secure HttpOnly cookie for browser protection against XSS
    response.set_cookie(
        key="dukaansaathi_session",
        value=signed_token,
        httponly=True,
        samesite="lax",
        secure=settings.ENABLE_HSTS,
        max_age=settings.SESSION_EXPIRE_SECONDS
    )

    return MerchantLoginResponse(
        access_token=signed_token,
        token_type="bearer",
        store_id=settings.DEMO_STORE_ID,
        merchant_name=store_name,
        expires_in=settings.SESSION_EXPIRE_SECONDS
    )


@router.get("/me", response_model=MerchantMeResponse)
def get_current_merchant_profile(
    current_merchant: Dict[str, Any] = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Validates current merchant bearer token and returns session identity.
    """
    store_id = current_merchant.get("store_id", settings.DEMO_STORE_ID)
    store = db.query(Store).filter(Store.store_id == store_id).first()
    store_name = store.store_name if store else "Everyday Needs General Store"

    return MerchantMeResponse(
        authenticated=True,
        store_id=store_id,
        merchant_name=store_name
    )


@router.post("/logout", response_model=MerchantLogoutResponse)
def merchant_logout(
    response: Response,
    authorization: Optional[str] = Header(None),
    x_merchant_token: Optional[str] = Header(None),
    current_merchant: Dict[str, Any] = Depends(get_current_merchant)
):
    """
    Terminates the active merchant session.
    Blacklists the session token server-side and clears secure session cookies.
    """
    token = None
    if authorization:
        parts = authorization.split(" ")
        token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    elif x_merchant_token:
        token = x_merchant_token

    if token:
        revoke_token(token)

    response.delete_cookie("dukaansaathi_session")

    return MerchantLogoutResponse(
        message="Merchant session terminated successfully. Credentials revoked server-side.",
        logged_out=True
    )
