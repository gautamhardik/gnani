"""
DukaanSaathi — Cart Management Service (Phase 3 Service 5)
Manages conversational draft shopping carts and calculates authoritative totals.
Prices are strictly sourced from the database.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from backend.app.schemas.intelligence import CartItem

class CartService:
    def __init__(self, initial_items: Optional[List[Dict[str, Any]]] = None):
        self.items: Dict[str, CartItem] = {}
        if initial_items:
            for it in initial_items:
                self.items[it["product_id"]] = CartItem(
                    product_id=it["product_id"],
                    name=it["name"],
                    quantity=Decimal(str(it["quantity"])),
                    unit=it["unit"],
                    unit_price=Decimal(str(it["unit_price"])),
                    subtotal=Decimal(str(it.get("subtotal", Decimal(str(it["quantity"])) * Decimal(str(it["unit_price"]))))),
                    requested_quantity=Decimal(str(it["requested_quantity"])) if it.get("requested_quantity") is not None else None,
                    requested_unit=it.get("requested_unit")
                )

    def add_or_update_item(
        self,
        product_id: str,
        name: str,
        quantity: Decimal,
        unit: str,
        unit_price: Decimal,
        requested_quantity: Optional[Decimal] = None,
        requested_unit: Optional[str] = None
    ) -> CartItem:
        """Adds product to cart or increments quantity if already present."""
        if product_id in self.items:
            existing = self.items[product_id]
            new_qty = existing.quantity + quantity
            new_subtotal = new_qty * unit_price
            existing.quantity = new_qty
            existing.subtotal = new_subtotal
            if requested_quantity and existing.requested_quantity:
                existing.requested_quantity += requested_quantity
            return existing

        subtotal = quantity * unit_price
        item = CartItem(
            product_id=product_id,
            name=name,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            subtotal=subtotal,
            requested_quantity=requested_quantity,
            requested_unit=requested_unit
        )
        self.items[product_id] = item
        return item

    def set_item_quantity(
        self,
        product_id: str,
        new_quantity: Decimal
    ) -> Optional[CartItem]:
        """Replaces pending item quantity (e.g. 'Nahi, aadha kilo kar do')."""
        if product_id not in self.items:
            return None

        item = self.items[product_id]
        if new_quantity <= 0:
            del self.items[product_id]
            return None

        item.quantity = new_quantity
        item.subtotal = new_quantity * item.unit_price
        return item

    def remove_item(self, product_id: str) -> bool:
        """Removes a product from the shopping cart (e.g. 'Maggi hata do')."""
        if product_id in self.items:
            del self.items[product_id]
            return True
        return False

    def clear(self):
        """Empties the cart."""
        self.items.clear()

    def get_items(self) -> List[CartItem]:
        return list(self.items.values())

    def calculate_total(self) -> Decimal:
        """Calculates authoritative total amount from database prices."""
        total = Decimal("0.00")
        for it in self.items.values():
            total += it.subtotal
        return total.quantize(Decimal("0.01"))

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Serializes cart for JSONB storage in order_sessions."""
        return [
            {
                "product_id": it.product_id,
                "name": it.name,
                "quantity": float(it.quantity),
                "unit": it.unit,
                "unit_price": float(it.unit_price),
                "subtotal": float(it.subtotal),
                "requested_quantity": float(it.requested_quantity) if it.requested_quantity is not None else None,
                "requested_unit": it.requested_unit
            }
            for it in self.items.values()
        ]
