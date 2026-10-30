from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    stock_quantity: Decimal
    stock_unit: str
    low_stock_threshold: Decimal
    reserved_quantity: Decimal
    is_low_stock: bool
    is_out_of_stock: bool
    updated_at: datetime

class InventoryUpdateRequest(BaseModel):
    stock_quantity: Decimal = Field(..., ge=0, description="New available stock quantity")
    low_stock_threshold: Optional[Decimal] = Field(None, ge=0)
    reason: str = Field(default="manual_adjustment", description="Audit reason for stock change")
