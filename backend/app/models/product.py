from sqlalchemy import Column, String, Numeric, Boolean, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship
from backend.app.models.base import Base

class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    brand = Column(String, nullable=True, index=True)
    category = Column(String, nullable=False, index=True)
    sale_unit = Column(String, nullable=False)
    pack_size = Column(Numeric(12, 3), nullable=False)
    pack_size_unit = Column(String, nullable=False)
    price_inr = Column(Numeric(12, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    description = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_store_sku"),
        CheckConstraint("price_inr >= 0", name="chk_positive_price"),
    )

    # Relationships
    store = relationship("Store", back_populates="products")
    aliases = relationship("ProductAlias", back_populates="product", cascade="all, delete-orphan")
    inventory = relationship("StoreInventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    stock_movements = relationship("StockMovement", back_populates="product")


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    alias_id = Column(String, primary_key=True, index=True)
    product_id = Column(String, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    alias = Column(String, nullable=False)
    normalized_alias = Column(String, nullable=False, index=True)
    language = Column(String, nullable=False, default="hi-Latn")
    alias_type = Column(String, nullable=False, default="colloquial")

    __table_args__ = (
        Index("idx_alias_normalized", "normalized_alias"),
    )

    # Relationships
    product = relationship("Product", back_populates="aliases")
