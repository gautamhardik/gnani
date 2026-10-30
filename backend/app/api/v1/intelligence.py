import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.models import OrderSession, Store
from backend.app.schemas.intelligence import TurnResponse
from backend.app.services import ConversationManager

router = APIRouter(prefix="/intelligence", tags=["Order Intelligence"])

class ProcessTurnRequest(BaseModel):
    utterance: str = Field(..., min_length=1, description="Raw transcribed customer utterance")
    session_id: Optional[str] = None
    store_id: Optional[str] = None
    customer_id: Optional[str] = None

@router.post("/process-turn", response_model=TurnResponse)
def process_conversation_turn(
    request: ProcessTurnRequest,
    db: Session = Depends(get_db)
):
    """
    Main dialogue turn endpoint:
    Converts transcribed speech into structured cart mutations,
    detects intent, checks inventory, and produces spoken response.
    """
    store_id = request.store_id or settings.DEMO_STORE_ID
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store '{store_id}' not found"
        )

    # Resolve or create OrderSession
    session_id = request.session_id or f"SESS{uuid.uuid4().hex[:8].upper()}"
    sess = db.query(OrderSession).filter(OrderSession.session_id == session_id).first()

    existing_cart = []
    if sess:
        existing_cart = sess.current_cart or []
    else:
        sess = OrderSession(
            session_id=session_id,
            store_id=store_id,
            customer_id=request.customer_id,
            status="active",
            current_cart=[]
        )
        db.add(sess)
        db.flush()

    # Process turn through conversation manager
    manager = ConversationManager(db=db, store_id=store_id)
    turn_response = manager.process_turn(
        session_id=session_id,
        user_utterance=request.utterance,
        existing_cart=existing_cart
    )

    # Update session cart in database
    sess.current_cart = [
        {
            "product_id": it.product_id,
            "name": it.name,
            "quantity": float(it.quantity),
            "unit": it.unit,
            "unit_price": float(it.unit_price),
            "subtotal": float(it.subtotal),
            "requested_quantity": float(it.requested_quantity) if it.requested_quantity is not None else None,
            "requested_unit": it.requested_unit
        }
        for it in turn_response.cart
    ]

    if turn_response.state.value == "ORDER_PLACED":
        sess.status = "confirmed"
    elif turn_response.state.value == "CANCELLED":
        sess.status = "expired"

    db.commit()

    return turn_response

