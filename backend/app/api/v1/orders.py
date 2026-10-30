import uuid
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.app.api.deps import get_db, get_current_merchant
from backend.app.core.config import settings
from backend.app.models import (
    Order,
    OrderItem,
    OrderSession,
    StoreInventory,
    Product,
    StockMovement,
)
from backend.app.schemas import (
    OrderCreateRequest,
    OrderResponse,
    OrderItemResponse,
    OrderRejectRequest,
    OrderStatusUpdateRequest,
    PaginatedResponse,
)

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_customer_order(
    order_in: OrderCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Customer Confirmation Endpoint:
    Creates a pending order from customer cart items.
    Authoritative prices and product names are snapshotted from PostgreSQL.
    CRITICAL BUSINESS RULE:
    - Order is created with status='pending'.
    - Inventory is NOT deducted at customer confirmation.
    - Deduction occurs strictly upon merchant acceptance.
    """
    store_id = order_in.store_id or settings.DEMO_STORE_ID

    if not order_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot place an order with an empty cart."
        )

    # Validate active products and compute authoritative prices
    total_amount = Decimal(0)
    items_to_create = []

    for item_in in order_in.items:
        prod = (
            db.query(Product)
            .options(joinedload(Product.inventory))
            .filter(Product.product_id == item_in.product_id, Product.store_id == store_id)
            .first()
        )
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{item_in.product_id}' not found in store"
            )
        if not prod.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{prod.name}' is currently inactive and cannot be ordered"
            )

        # Pre-check initial stock availability (does NOT lock or deduct yet)
        inv = prod.inventory
        if not inv or inv.stock_quantity < item_in.quantity:
            avail = inv.stock_quantity if inv else 0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{prod.name}': requested {item_in.quantity}, currently available {avail}"
            )

        unit_price = prod.price_inr
        subtotal = unit_price * item_in.quantity
        total_amount += subtotal

        items_to_create.append({
            "product_id": prod.product_id,
            "product_name_snapshot": prod.name,
            "quantity": item_in.quantity,
            "unit": prod.sale_unit,
            "unit_price": unit_price,
            "subtotal": subtotal
        })

    # Create Order Header
    order_id = f"ORD{uuid.uuid4().hex[:8].upper()}"
    order = Order(
        order_id=order_id,
        store_id=store_id,
        session_id=order_in.session_id,
        customer_id=order_in.customer_id,
        total_amount=total_amount,
        status="pending"  # PENDING MERCHANT ACCEPTANCE
    )
    db.add(order)
    db.flush()

    # Create Order Items Snapshot
    created_items = []
    for it in items_to_create:
        order_item = OrderItem(
            item_id=f"ITM{uuid.uuid4().hex[:8].upper()}",
            order_id=order_id,
            product_id=it["product_id"],
            product_name_snapshot=it["product_name_snapshot"],
            quantity=it["quantity"],
            unit=it["unit"],
            unit_price=it["unit_price"],
            subtotal=it["subtotal"]
        )
        db.add(order_item)
        created_items.append(order_item)

    # Mark session as confirmed if provided
    if order_in.session_id:
        sess = db.query(OrderSession).filter(OrderSession.session_id == order_in.session_id).first()
        if sess:
            sess.status = "confirmed"

    # Commit pending order; notice stock is untouched!
    db.commit()
    db.refresh(order)

    return order


@router.get("", response_model=PaginatedResponse[OrderResponse])
def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    order_status: Optional[str] = Query(None, alias="status"),
    store_id: str = settings.DEMO_STORE_ID,
    db: Session = Depends(get_db)
):
    """Lists orders with status filter (Merchant Dashboard Feed)."""
    query = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.store_id == store_id)
    )

    if order_status:
        query = query.filter(Order.status == order_status)

    total = query.count()
    offset = (page - 1) * size
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(size).all()

    return PaginatedResponse(
        items=orders,
        total=total,
        page=page,
        size=size,
        has_more=(offset + len(orders)) < total
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves order details, snapshotted prices, and items."""
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.order_id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found"
        )
    return order


@router.post("/{order_id}/accept", response_model=OrderResponse)
def accept_order(
    order_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_merchant)
):
    """
    Merchant Acceptance Endpoint:
    CRITICAL BUSINESS RULE:
    1. Rechecks live inventory for all items in order.
    2. Atomically decrements stock inside transaction.
    3. Records audit log in stock_movements (reason='merchant_order_accepted').
    4. Transitions order status from 'pending' to 'accepted'.
    5. Fails and rolls back if any SKU has insufficient stock.
    """
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.order_id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only orders in 'pending' status can be accepted. Current status: '{order.status}'"
        )

    # Atomic stock recheck and deduction
    for item in order.items:
        inv = db.query(StoreInventory).filter(StoreInventory.product_id == item.product_id).with_for_update().first()
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No inventory record found for product '{item.product_name_snapshot}' ({item.product_id})"
            )

        if inv.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{item.product_name_snapshot}': requested {item.quantity}, available {inv.stock_quantity}. Cannot accept order."
            )

        # Decrement stock atomically
        inv.stock_quantity -= item.quantity

        # Record stock movement audit
        movement = StockMovement(
            movement_id=f"MOV{uuid.uuid4().hex[:8].upper()}",
            product_id=item.product_id,
            order_id=order.order_id,
            change_quantity=-item.quantity,
            reason="merchant_order_accepted"
        )
        db.add(movement)

    order.status = "accepted"
    db.commit()
    db.refresh(order)

    return order


@router.post("/{order_id}/reject", response_model=OrderResponse)
def reject_order(
    order_id: str,
    reject_in: Optional[OrderRejectRequest] = None,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_merchant)
):
    """
    Merchant Rejection Endpoint:
    Rejects a pending order with a specified reason.
    Since stock was not deducted during pending creation, no compensating inventory movement is required.
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only orders in 'pending' status can be rejected. Current status: '{order.status}'"
        )

    reason = reject_in.reason if reject_in and reject_in.reason else "Order rejected by merchant"
    order.status = "rejected"
    order.rejection_reason = reason
    db.commit()
    db.refresh(order)

    return order


@router.post("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: str,
    status_in: OrderStatusUpdateRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_merchant)
):
    """
    Merchant Order Lifecycle Transition Endpoint:
    Enforces valid state machine transitions:
    - accepted -> preparing
    - preparing -> ready
    - ready -> completed
    - accepted / preparing / ready -> cancelled (with compensating stock restoration)
    Rejects invalid transitions (e.g. pending directly to completed).
    """
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.order_id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found"
        )

    current_status = order.status
    target_status = status_in.status.lower()

    valid_transitions = {
        "accepted": ["preparing", "cancelled"],
        "preparing": ["ready", "cancelled"],
        "ready": ["completed", "cancelled"],
    }

    if current_status not in valid_transitions or target_status not in valid_transitions[current_status]:
        allowed = valid_transitions.get(current_status, [])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current_status}' to '{target_status}'. Allowed transitions: {allowed}"
        )

    # Compensating stock restoration if order was accepted and is now cancelled
    if target_status == "cancelled" and current_status in ["accepted", "preparing", "ready"]:
        for item in order.items:
            inv = db.query(StoreInventory).filter(StoreInventory.product_id == item.product_id).with_for_update().first()
            if inv:
                inv.stock_quantity += item.quantity
                movement = StockMovement(
                    movement_id=f"MOV{uuid.uuid4().hex[:8].upper()}",
                    product_id=item.product_id,
                    order_id=order.order_id,
                    change_quantity=item.quantity,
                    reason="order_cancelled_restock"
                )
                db.add(movement)

    order.status = target_status
    if status_in.notes:
        order.rejection_reason = status_in.notes

    db.commit()
    db.refresh(order)
    return order
