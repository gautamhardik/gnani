"""
DukaanSaathi — Merchant Dashboard Schemas
"""

from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.order import OrderResponse

class MerchantOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: str
    store_name: str
    pending_orders_count: int
    today_orders_count: int
    completed_orders_count: int
    total_sales_inr: Decimal
    low_stock_products_count: int
    out_of_stock_count: int
    total_products_count: int
    recent_orders: List[OrderResponse] = []
    generated_at: datetime

