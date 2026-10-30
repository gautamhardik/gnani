"""
DukaanSaathi — Customer Session & Cart Management API Router
Manages customer session lifecycle, authoritative cart state, and manual cart edits.
Ensures prices and availability are strictly backed by PostgreSQL/SQLite.
"""

import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.models import OrderSession, Store, Product, StoreInventory
from backend.app.schemas.order import (
    OrderSessionCreate,
    OrderSessionResponse,
    OrderSessionDetailResponse,
    UpdateCartItemRequest,
)
from backend.app.services.cart_service import CartService

router = APIRouter(prefix="/sessions", tags=["Customer Sessions"])


@router.post("", response_model=OrderSessionResponse, status_code=status.HTTP_201_CREATED)
def create_customer_session(
    session_in: OrderSessionCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new customer order session.
    Preserves session ID between turns and supports multiple consecutive recordings.
    """
    store_id = session_in.store_id or settings.DEMO_STORE_ID
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        # Check if demo store fallback
        if store_id != settings.DEMO_STORE_ID:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store '{store_id}' not found"
            )

    session_id = f"SESS{uuid.uuid4().hex[:8].upper()}"
    sess = OrderSession(
        session_id=session_id,
        store_id=store_id,
        customer_id=session_in.customer_id,
        status="active",
        current_cart=[]
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


@router.get("/{session_id}", response_model=OrderSessionDetailResponse)
def get_session_details(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves customer session state, current cart, and server-calculated authoritative total.
    """
    sess = db.query(OrderSession).filter(OrderSession.session_id == session_id).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    cart_service = CartService(sess.current_cart or [])
    total_amount = cart_service.calculate_total()
    items = cart_service.get_items()

    # Convert to serialized dicts
    serialized_cart = [
        {
            "product_id": it.product_id,
            "name": it.name,
            "quantity": float(it.quantity),
            "unit": it.unit,
            "unit_price": float(it.unit_price),
            "subtotal": float(it.subtotal),
            "requested_quantity": float(it.requested_quantity) if it.requested_quantity else None,
            "requested_unit": it.requested_unit
        }
        for it in items
    ]

    return OrderSessionDetailResponse(
        session_id=sess.session_id,
        store_id=sess.store_id,
        customer_id=sess.customer_id,
        status=sess.status,
        current_cart=serialized_cart,
        total_amount=total_amount,
        item_count=len(serialized_cart),
        created_at=sess.created_at,
        updated_at=sess.updated_at
    )


@router.put("/{session_id}/cart/items/{product_id}", response_model=OrderSessionDetailResponse)
def update_session_cart_item(
    session_id: str,
    product_id: str,
    item_in: UpdateCartItemRequest,
    db: Session = Depends(get_db)
):
    """
    Manual cart quantity update via authoritative backend.
    Never allows browser to invent prices or bypass inventory validation.
    """
    sess = db.query(OrderSession).filter(OrderSession.session_id == session_id).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    if sess.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is '{sess.status}' and cannot be modified."
        )

    cart_service = CartService(sess.current_cart or [])

    if item_in.quantity <= Decimal("0"):
        # Remove item
        cart_service.remove_item(product_id)
    else:
        # Validate product and stock
        prod = (
            db.query(Product)
            .options(joinedload(Product.inventory))
            .filter(Product.product_id == product_id, Product.store_id == sess.store_id)
            .first()
        )
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product '{product_id}' not found in store"
            )
        if not prod.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{prod.name}' is inactive"
            )

        inv = prod.inventory
        if not inv or inv.stock_quantity < item_in.quantity:
            avail = inv.stock_quantity if inv else 0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{prod.name}': requested {item_in.quantity}, available {avail}"
            )

        if product_id in cart_service.items:
            cart_service.set_item_quantity(product_id, item_in.quantity)
        else:
            cart_service.add_or_update_item(
                product_id=prod.product_id,
                name=prod.name,
                quantity=item_in.quantity,
                unit=prod.sale_unit,
                unit_price=prod.price_inr
            )

    items = cart_service.get_items()
    serialized_cart = [
        {
            "product_id": it.product_id,
            "name": it.name,
            "quantity": float(it.quantity),
            "unit": it.unit,
            "unit_price": float(it.unit_price),
            "subtotal": float(it.subtotal),
            "requested_quantity": float(it.requested_quantity) if it.requested_quantity else None,
            "requested_unit": it.requested_unit
        }
        for it in items
    ]

    sess.current_cart = serialized_cart
    db.commit()
    db.refresh(sess)

    return OrderSessionDetailResponse(
        session_id=sess.session_id,
        store_id=sess.store_id,
        customer_id=sess.customer_id,
        status=sess.status,
        current_cart=serialized_cart,
        total_amount=cart_service.calculate_total(),
        item_count=len(serialized_cart),
        created_at=sess.created_at,
        updated_at=sess.updated_at
    )


@router.delete("/{session_id}/cart/items/{product_id}", response_model=OrderSessionDetailResponse)
def remove_session_cart_item(
    session_id: str,
    product_id: str,
    db: Session = Depends(get_db)
):
    """
    Removes an item from the customer's draft cart.
    """
    sess = db.query(OrderSession).filter(OrderSession.session_id == session_id).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    if sess.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is '{sess.status}' and cannot be modified."
        )

    cart_service = CartService(sess.current_cart or [])
    cart_service.remove_item(product_id)

    items = cart_service.get_items()
    serialized_cart = [
        {
            "product_id": it.product_id,
            "name": it.name,
            "quantity": float(it.quantity),
            "unit": it.unit,
            "unit_price": float(it.unit_price),
            "subtotal": float(it.subtotal),
            "requested_quantity": float(it.requested_quantity) if it.requested_quantity else None,
            "requested_unit": it.requested_unit
        }
        for it in items
    ]

    sess.current_cart = serialized_cart
    db.commit()
    db.refresh(sess)

    return OrderSessionDetailResponse(
        session_id=sess.session_id,
        store_id=sess.store_id,
        customer_id=sess.customer_id,
        status=sess.status,
        current_cart=serialized_cart,
        total_amount=cart_service.calculate_total(),
        item_count=len(serialized_cart),
        created_at=sess.created_at,
        updated_at=sess.updated_at
    )

