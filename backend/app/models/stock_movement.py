from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import Base

class StockMovement(Base):
    __tablename__ = "stock_movements"

    movement_id = Column(String, primary_key=True, index=True)
    product_id = Column(String, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(String, ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True, index=True)
    change_quantity = Column(Numeric(12, 3), nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="stock_movements")
    order = relationship("Order", back_populates="stock_movements")
