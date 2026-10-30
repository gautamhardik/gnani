"""
DukaanSaathi — Inventory Integration Service (Phase 3 Service 7)
Provides authoritative stock checks and database pricing lookups.
CRITICAL INVARIANT: Never deducts inventory or mutates stock tables at this stage.
"""

from decimal import Decimal
from typing import Tuple, Optional
from sqlalchemy.orm import Session

from backend.app.models import StoreInventory, Product

class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def check_availability(
        self,
        product_id: str,
        requested_quantity: Decimal
    ) -> Tuple[bool, Decimal, Decimal]:
        """
        Validates inventory for a requested SKU without altering stock.
        Returns: (is_available, current_stock, low_stock_threshold)
        """
        inv = (
            self.db.query(StoreInventory)
            .filter(StoreInventory.product_id == product_id)
            .first()
        )
        if not inv:
            return False, Decimal(0), Decimal(0)

        current_stock = inv.stock_quantity
        threshold = inv.low_stock_threshold

        is_available = current_stock >= requested_quantity
        return is_available, current_stock, threshold

    def get_product_details(self, product_id: str) -> Optional[Product]:
        """Retrieves authoritative product record."""
        return self.db.query(Product).filter(Product.product_id == product_id).first()

    def get_authoritative_price(self, product_id: str) -> Optional[Decimal]:
        """Retrieves authoritative product unit price from PostgreSQL/SQLite."""
        prod = self.get_product_details(product_id)
        return Decimal(str(prod.price_inr)) if prod else None

