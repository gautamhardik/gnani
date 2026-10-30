"""
DukaanSaathi — Store Schemas
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: str
    store_name: str
    slug: str
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    is_open: bool = True
    opening_time: str = "08:00 AM"
    closing_time: str = "10:00 PM"
    contact_display: str = "Demo store — Sharma General Store"
    description: str = "Voice-first neighbourhood kirana store"
    supported_languages: List[str] = ["hi-IN", "hi-en", "en-IN"]
    created_at: Optional[datetime] = None

