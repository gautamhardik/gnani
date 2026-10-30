"""
DukaanSaathi — Merchant Authentication Router
Provides secure backend-mediated login for the shopkeeper operations portal.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_current_merchant
from backend.app.core.config import settings
from backend.app.models import Store
from backend.app.schemas.auth import (
    MerchantLoginRequest,
    MerchantLoginResponse,
    MerchantMeResponse,
)

router = APIRouter(prefix="/auth", tags=["Merchant Authentication"])


@router.post("/login", response_model=MerchantLoginResponse)
def merchant_login(
    login_in: MerchantLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticates shopkeeper credentials and returns a protected bearer access token.
    Credentials are authenticated securely on the backend without exposure to client bundles.
    """
    if (
        login_in.username != settings.MERCHANT_USERNAME
        or login_in.password != settings.MERCHANT_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Galat username ya password. Kripya sahi credentials daalein.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    store = db.query(Store).filter(Store.store_id == settings.DEMO_STORE_ID).first()
    store_name = store.store_name if store else "Sharma General Store"

    return MerchantLoginResponse(
        access_token=settings.SHOPKEEPER_AUTH_TOKEN,
        token_type="bearer",
        store_id=settings.DEMO_STORE_ID,
        merchant_name=store_name
    )


@router.get("/me", response_model=MerchantMeResponse)
def get_current_merchant_profile(
    _: bool = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    """
    Validates current merchant bearer token and returns session identity.
    """
    store = db.query(Store).filter(Store.store_id == settings.DEMO_STORE_ID).first()
    store_name = store.store_name if store else "Sharma General Store"

    return MerchantMeResponse(
        authenticated=True,
        store_id=settings.DEMO_STORE_ID,
        merchant_name=store_name
    )

