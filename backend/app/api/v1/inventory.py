import uuid
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.app.api.deps import get_db, get_current_merchant
from backend.app.models import StoreInventory, Product, StockMovement
from backend.app.schemas import (
    InventoryResponse,
    InventoryUpdateRequest,
    StockMovementResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("", response_model=PaginatedResponse[InventoryResponse])
def list_inventory(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    only_low_stock: bool = False,
    only_out_of_stock: bool = False,
    db: Session = Depends(get_db)
):
    """Lists store inventory with threshold alerts."""
    query = db.query(StoreInventory).join(Product, StoreInventory.product_id == Product.product_id)

    if only_out_of_stock:
        query = query.filter(StoreInventory.stock_quantity == 0)
    elif only_low_stock:
        query = query.filter(StoreInventory.stock_quantity <= StoreInventory.low_stock_threshold)

    total = query.count()
    offset = (page - 1) * size
    items = query.order_by(StoreInventory.product_id).offset(offset).limit(size).all()

    inv_list = [
        InventoryResponse(
            product_id=inv.product_id,
            stock_quantity=inv.stock_quantity,
            stock_unit=inv.stock_unit,
            low_stock_threshold=inv.low_stock_threshold,
            reserved_quantity=inv.reserved_quantity,
            is_low_stock=inv.stock_quantity <= inv.low_stock_threshold,
            is_out_of_stock=inv.stock_quantity == 0,
            updated_at=inv.updated_at
        )
        for inv in items
    ]

    return PaginatedResponse(
        items=inv_list,
        total=total,
        page=page,
        size=size,
        has_more=(offset + len(inv_list)) < total
    )


@router.get("/movements", response_model=PaginatedResponse[StockMovementResponse])
def list_stock_movements(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    product_id: Optional[str] = None,
    order_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_merchant)
):
    """
    Lists recorded stock movements and audit reasons (Merchant Protected).
    """
    query = db.query(StockMovement).options(joinedload(StockMovement.product))
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    if order_id:
        query = query.filter(StockMovement.order_id == order_id)

    total = query.count()
    offset = (page - 1) * size
    movements = query.order_by(StockMovement.created_at.desc()).offset(offset).limit(size).all()

    items = [
        StockMovementResponse(
            movement_id=m.movement_id,
            product_id=m.product_id,
            product_name=m.product.name if m.product else None,
            order_id=m.order_id,
            change_quantity=m.change_quantity,
            reason=m.reason,
            created_at=m.created_at
        )
        for m in movements
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        has_more=(offset + len(items)) < total
    )


@router.get("/{product_id}", response_model=InventoryResponse)
def get_inventory_item(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves current stock level and reservation metrics for a specific product."""
    inv = db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory record for product '{product_id}' not found"
        )

    return InventoryResponse(
        product_id=inv.product_id,
        stock_quantity=inv.stock_quantity,
        stock_unit=inv.stock_unit,
        low_stock_threshold=inv.low_stock_threshold,
        reserved_quantity=inv.reserved_quantity,
        is_low_stock=inv.stock_quantity <= inv.low_stock_threshold,
        is_out_of_stock=inv.stock_quantity == 0,
        updated_at=inv.updated_at
    )


@router.put("/{product_id}", response_model=InventoryResponse)
def update_inventory_stock(
    product_id: str,
    update_in: InventoryUpdateRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_merchant)
):
    """
    Updates product stock level and records an authoritative audit row in stock_movements (Merchant Protected).
    """
    inv = db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory record for product '{product_id}' not found"
        )

    old_stock = inv.stock_quantity
    new_stock = update_in.stock_quantity
    diff = new_stock - old_stock

    inv.stock_quantity = new_stock
    if update_in.low_stock_threshold is not None:
        inv.low_stock_threshold = update_in.low_stock_threshold

    # Record stock movement audit
    if diff != 0:
        movement = StockMovement(
            movement_id=f"MOV{uuid.uuid4().hex[:8].upper()}",
            product_id=product_id,
            order_id=None,
            change_quantity=diff,
            reason=update_in.reason or "manual_adjustment"
        )
        db.add(movement)

    db.commit()
    db.refresh(inv)

    return InventoryResponse(
        product_id=inv.product_id,
        stock_quantity=inv.stock_quantity,
        stock_unit=inv.stock_unit,
        low_stock_threshold=inv.low_stock_threshold,
        reserved_quantity=inv.reserved_quantity,
        is_low_stock=inv.stock_quantity <= inv.low_stock_threshold,
        is_out_of_stock=inv.stock_quantity == 0,
        updated_at=inv.updated_at
    )
