from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    has_more: bool

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
