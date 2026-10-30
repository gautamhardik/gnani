from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from backend.app.models.base import Base

class StoreInventory(Base):
    __tablename__ = "inventory"

    product_id = Column(String, ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    stock_quantity = Column(Numeric(12, 3), nullable=False, default=0)
    stock_unit = Column(String, nullable=False)
    low_stock_threshold = Column(Numeric(12, 3), nullable=False, default=0)
    reserved_quantity = Column(Numeric(12, 3), nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("stock_quantity >= 0", name="chk_non_negative_stock"),
        CheckConstraint("reserved_quantity >= 0", name="chk_non_negative_reserved"),
    )

    # Relationships
    product = relationship("Product", back_populates="inventory")
