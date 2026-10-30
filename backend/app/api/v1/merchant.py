"""
DukaanSaathi — Merchant Operations & Overview Router
Computes live operational metrics and dashboard statistics directly from authoritative database models.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from backend.app.api.deps import get_db, get_current_merchant
from backend.app.core.config import settings
from backend.app.models import Store, Order, Product, StoreInventory
from backend.app.schemas.merchant import MerchantOverviewResponse

router = APIRouter(prefix="/merchant", tags=["Merchant Operations"])


@router.get("/overview", response_model=MerchantOverviewResponse)
def get_merchant_overview(
    store_id: str = settings.DEMO_STORE_ID,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_merchant)
):
    """
    Returns live operational metrics for the merchant dashboard:
    - Pending orders awaiting acceptance
    - Today's order volume
    - Completed orders count
    - Realized gross sales in INR
    - Inventory alert counts (low stock / out of stock)
    - Recent orders feed
    Never returns hardcoded or fabricated statistics.
    """
    store = db.query(Store).filter(Store.store_id == store_id).first()
    store_name = store.store_name if store else "Sharma General Store"

    # 1. Pending orders
    pending_count = (
        db.query(Order)
        .filter(Order.store_id == store_id, Order.status == "pending")
        .count()
    )

    # 2. Today's orders (IST / UTC start of day)
    now_utc = datetime.now(timezone.utc)
    # Start of today (UTC minus 24 hours window or midnight)
    midnight_utc = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    today_orders_count = (
        db.query(Order)
        .filter(Order.store_id == store_id, Order.created_at >= midnight_utc)
        .count()
    )

    # 3. Completed orders count
    completed_count = (
        db.query(Order)
        .filter(Order.store_id == store_id, Order.status == "completed")
        .count()
    )

    # 4. Total sales: sum of accepted, preparing, ready, completed orders
    sales_query = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.store_id == store_id,
            Order.status.in_(["accepted", "preparing", "ready", "completed"])
        )
        .scalar()
    )
    total_sales = Decimal(str(sales_query or "0.00")).quantize(Decimal("0.01"))

    # 5. Inventory alerts
    low_stock_count = (
        db.query(StoreInventory)
        .join(Product, StoreInventory.product_id == Product.product_id)
        .filter(
            Product.store_id == store_id,
            StoreInventory.stock_quantity <= StoreInventory.low_stock_threshold
        )
        .count()
    )

    out_of_stock_count = (
        db.query(StoreInventory)
        .join(Product, StoreInventory.product_id == Product.product_id)
        .filter(Product.store_id == store_id, StoreInventory.stock_quantity == 0)
        .count()
    )

    total_products_count = (
        db.query(Product)
        .filter(Product.store_id == store_id)
        .count()
    )

    # 6. Recent 5 orders with items loaded
    recent_orders = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.store_id == store_id)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    return MerchantOverviewResponse(
        store_id=store_id,
        store_name=store_name,
        pending_orders_count=pending_count,
        today_orders_count=today_orders_count,
        completed_orders_count=completed_count,
        total_sales_inr=total_sales,
        low_stock_products_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        total_products_count=total_products_count,
        recent_orders=recent_orders,
        generated_at=now_utc
    )
