"""
DukaanSaathi — Merchant Authentication Schemas (Phase 9 Hardening)
"""

from typing import Optional
from pydantic import BaseModel, Field

class MerchantLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Merchant username")
    password: str = Field(..., min_length=1, description="Merchant password")

class MerchantLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    store_id: str
    merchant_name: str
    expires_in: Optional[int] = Field(default=86400, description="Token lifespan in seconds")

class MerchantMeResponse(BaseModel):
    authenticated: bool
    store_id: str
    merchant_name: str

class MerchantLogoutResponse(BaseModel):
    message: str
    logged_out: bool = True
