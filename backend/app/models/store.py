from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from backend.app.models.base import Base

class Store(Base):
    __tablename__ = "stores"

    store_id = Column(String, primary_key=True, index=True)
    store_name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    currency = Column(String(3), nullable=False, default="INR")
    timezone = Column(String, nullable=False, default="Asia/Kolkata")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    order_sessions = relationship("OrderSession", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store", cascade="all, delete-orphan")
