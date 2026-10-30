"""
DukaanSaathi — Merchant Authentication Schemas
"""

from pydantic import BaseModel, Field

class MerchantLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Merchant username")
    password: str = Field(..., min_length=1, description="Merchant password")

class MerchantLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    store_id: str
    merchant_name: str

class MerchantMeResponse(BaseModel):
    authenticated: bool
    store_id: str
    merchant_name: str
