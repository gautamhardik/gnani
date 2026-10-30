from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.inventory import InventoryResponse

class ProductAliasBase(BaseModel):
    alias: str
    normalized_alias: str
    language: str = "hi-Latn"
    alias_type: str = "colloquial"

class ProductAliasResponse(ProductAliasBase):
    model_config = ConfigDict(from_attributes=True)

    alias_id: str
    product_id: str

class ProductBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    sale_unit: str = Field(..., min_length=1, max_length=50)
    pack_size: Decimal = Field(..., gt=0)
    pack_size_unit: str = Field(..., min_length=1, max_length=50)
    price_inr: Decimal = Field(..., ge=0)
    is_active: bool = True
    description: Optional[str] = None

class ProductCreate(ProductBase):
    product_id: Optional[str] = None
    store_id: Optional[str] = None
    initial_stock: Decimal = Field(default=Decimal(0), ge=0)
    low_stock_threshold: Decimal = Field(default=Decimal(0), ge=0)
    aliases: Optional[List[str]] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    sale_unit: Optional[str] = None
    pack_size: Optional[Decimal] = Field(None, gt=0)
    pack_size_unit: Optional[str] = None
    price_inr: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None
    description: Optional[str] = None

class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    store_id: str
    inventory: Optional[InventoryResponse] = None
    aliases: List[ProductAliasResponse] = []

class ProductSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    name: str
    brand: Optional[str] = None
    category: str
    sale_unit: str
    pack_size: Decimal
    pack_size_unit: str
    price_inr: Decimal
    is_active: bool
    stock_quantity: Decimal
    matched_alias: Optional[str] = None
    match_source: str = "canonical"  # "canonical", "brand", "alias"
