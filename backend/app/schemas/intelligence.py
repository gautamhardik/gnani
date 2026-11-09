"""
DukaanSaathi — Order Intelligence Engine Schemas (Phase 3)
Data contracts for transcript normalization, product matching,
quantity parsing, intent classification, and conversation state management.
"""

from enum import Enum
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class IntentType(str, Enum):
    ADD = "add_items"
    REMOVE = "remove_item"
    SET_QUANTITY = "set_quantity"
    REPLACE_QUANTITY = "replace_quantity"
    PRICE_QUERY = "quote_price"
    STOCK_QUERY = "quote_stock"
    CONFIRM = "confirm_order"
    CANCEL = "cancel_order"
    UNKNOWN = "unknown"


class DialogueState(str, Enum):
    COLLECTING = "COLLECTING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    ORDER_PLACED = "ORDER_PLACED"
    CANCELLED = "CANCELLED"


class ClarificationType(str, Enum):
    PRODUCT = "clarify_product"
    SIZE = "clarify_size"
    QUANTITY = "clarify_quantity"
    UNIT = "clarify_unit"
    INSUFFICIENT_STOCK = "clarify_insufficient_stock"
    UNSUPPORTED_PACKAGE_FRACTION = "clarify_package_fraction"
    PRODUCT_NOT_FOUND = "product_not_found"


class NormalizedTranscript(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    raw_transcript: str
    clean_text: str
    tokens: List[str]
    has_correction: bool = False
    correction_pre: Optional[str] = None
    correction_post: Optional[str] = None


class ExtractedQuantity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    raw_amount: Optional[Decimal] = None
    raw_unit: Optional[str] = None
    normalized_amount: Optional[Decimal] = None
    normalized_unit: Optional[str] = None
    is_unmeasurable: bool = False  # e.g. "thoda sa"
    is_explicit: bool = False  # True when an explicit number, word, fraction, or currency amount was uttered
    rupee_amount: Optional[Decimal] = None  # e.g. "23 rupaye ki cheeni"


class ProductMatchCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    name: str
    brand: Optional[str] = None
    category: str
    sale_unit: str
    pack_size: Decimal
    pack_size_unit: str
    price_inr: Decimal
    confidence: float
    matched_text: str
    match_source: str  # "exact_alias", "exact_name", "fuzzy_alias", "fuzzy_name"
    is_generic: bool = False


class ProductMatchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    matched: bool
    product: Optional[ProductMatchCandidate] = None
    candidates: List[ProductMatchCandidate] = []
    is_ambiguous: bool = False
    clarification_type: Optional[ClarificationType] = None
    clarification_options: List[str] = []
    reason: Optional[str] = None

    @property
    def product_id(self) -> Optional[str]:
        return self.product.product_id if self.product else None


class CartItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    name: str
    quantity: Decimal = Field(..., gt=0)
    unit: str
    unit_price: Decimal
    subtotal: Decimal
    requested_quantity: Optional[Decimal] = None
    requested_unit: Optional[str] = None


class TurnAction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str  # e.g. "add_items", "remove_item", "clarify_product", "quote_price", etc.
    items: List[CartItem] = []
    message: str
    clarification_type: Optional[ClarificationType] = None
    clarification_options: List[str] = []
    price_quote: Optional[Decimal] = None
    stock_quote: Optional[Decimal] = None


class TurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    intent: IntentType
    state: DialogueState
    action: TurnAction
    cart: List[CartItem]
    total_amount: Decimal
    spoken_response: str
