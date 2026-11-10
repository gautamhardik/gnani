from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, CheckConstraint, JSON, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import Base

class OrderSession(Base):
    __tablename__ = "order_sessions"

    session_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="active")
    current_cart = Column(JSON, nullable=False, default=list)
    conversation_history = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("status IN ('active', 'confirmed', 'expired')", name="chk_session_status"),
    )

    # Relationships
    store = relationship("Store", back_populates="order_sessions")
    customer = relationship("Customer", back_populates="order_sessions")
    orders = relationship("Order", back_populates="session")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("order_sessions.session_id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(String, ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String, nullable=False, default="pending", index=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="chk_positive_order_total"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'preparing', 'ready', 'completed', 'rejected', 'cancelled')",
            name="chk_order_status"
        ),
    )

    # Relationships
    store = relationship("Store", back_populates="orders")
    session = relationship("OrderSession", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovement", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    item_id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False, index=True)
    product_name_snapshot = Column(String, nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit = Column(String, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_positive_quantity"),
        CheckConstraint("unit_price >= 0", name="chk_positive_unit_price"),
        CheckConstraint("subtotal >= 0", name="chk_positive_subtotal"),
    )

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
