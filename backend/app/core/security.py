"""
DukaanSaathi — Security & Access Control
Protects shopkeeper administrative APIs.
"""

from fastapi import Header, HTTPException, status
from backend.app.core.config import settings

def verify_merchant_token(
    authorization: str = Header(None),
    x_merchant_token: str = Header(None)
):
    """
    Validates that incoming requests to administrative endpoints carry a valid merchant token.
    Accepts:
    1. Authorization: Bearer <token>
    2. x-merchant-token: <token>
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

    if not token or token != settings.SHOPKEEPER_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing merchant authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
