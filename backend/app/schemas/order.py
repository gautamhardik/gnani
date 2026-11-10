from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

class CartItemSchema(BaseModel):
    product_id: str
    quantity: Decimal = Field(..., gt=0)
    unit: str
    requested_quantity: Optional[Decimal] = None
    requested_unit: Optional[str] = None

class OrderSessionCreate(BaseModel):
    store_id: Optional[str] = None
    customer_id: Optional[str] = None

class OrderSessionUpdate(BaseModel):
    status: Optional[str] = None
    current_cart: Optional[List[dict]] = None

class OrderSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    store_id: str
    customer_id: Optional[str] = None
    status: str
    current_cart: List[Any]
    conversation_history: List[Any] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class UpdateCartItemRequest(BaseModel):
    quantity: Decimal = Field(..., ge=0, description="New quantity. Set to 0 to remove item.")

class OrderSessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    store_id: str
    customer_id: Optional[str] = None
    status: str
    current_cart: List[Any]
    conversation_history: List[Any] = Field(default_factory=list)
    total_amount: Decimal = Field(default=Decimal("0.00"))
    item_count: int = Field(default=0)
    created_at: datetime
    updated_at: datetime

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: Decimal = Field(..., gt=0)

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    order_id: str
    product_id: str
    product_name_snapshot: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    subtotal: Decimal

class OrderCreateRequest(BaseModel):
    store_id: Optional[str] = None
    session_id: Optional[str] = None
    customer_id: Optional[str] = None
    items: List[OrderItemCreate] = Field(..., min_length=1)

class OrderRejectRequest(BaseModel):
    reason: Optional[str] = Field(default="Order rejected by merchant", description="Reason for merchant rejection")

class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: preparing, ready, completed, cancelled")
    notes: Optional[str] = Field(default=None, description="Optional notes on status transition")

class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    store_id: str
    session_id: Optional[str] = None
    customer_id: Optional[str] = None
    total_amount: Decimal
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime
    items: List[OrderItemResponse] = []
    conversation_history: Optional[List[Any]] = None
