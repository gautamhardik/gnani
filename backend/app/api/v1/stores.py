"""
DukaanSaathi — Stores API Router
Provides store profile, operating hours, language preferences, and open/closed status.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.models import Store
from backend.app.schemas.store import StoreResponse

router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("/{store_id}", response_model=StoreResponse)
def get_store_details(
    store_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns store profile, open/closed configuration, contact information,
    and supported language preferences.
    """
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        # If demo store requested before seed or custom ID
        if store_id == settings.DEMO_STORE_ID:
            return StoreResponse(
                store_id=settings.DEMO_STORE_ID,
                store_name="Everyday Needs General Store",
                slug="everyday-needs-general-store",
                currency="INR",
                timezone="Asia/Kolkata",
                is_open=True,
                opening_time="08:00 AM",
                closing_time="10:00 PM",
                contact_display="Everyday Needs General Store, Main Market",
                description="Aapki apni kirana dukaan — ab voice ordering ke saath.",
                supported_languages=["hi-IN", "hi-en", "en-IN"]
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store '{store_id}' not found"
        )

    return StoreResponse(
        store_id=store.store_id,
        store_name=store.store_name,
        slug=store.slug,
        currency=store.currency or "INR",
        timezone=store.timezone or "Asia/Kolkata",
        is_open=True,
        opening_time="08:00 AM",
        closing_time="10:00 PM",
        contact_display=f"{store.store_name}, Main Market",
        description="Aapki apni kirana dukaan — ab voice ordering ke saath.",
        supported_languages=["hi-IN", "hi-en", "en-IN"],
        created_at=store.created_at
    )

