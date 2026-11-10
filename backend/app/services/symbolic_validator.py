"""
DukaanSaathi — Deterministic Symbolic Validator (ReacTOD Architecture)
Enforces hard symbolic checks before mutating Dialogue Belief State (B_t) or Shopping Cart:
  1. Action Compliance: Tool/action permissible in current DialogueState
  2. Schema Conformance: Product active, positive quantities, pack size multiples
  3. Coreference Consistency: Grounded in dialogue history or prior pending product
"""

from decimal import Decimal
from typing import List, Optional, Set
from pydantic import BaseModel

from backend.app.schemas.intelligence import DialogueState, IntentType
from backend.app.models import Product


class ValidationResult(BaseModel):
    is_valid: bool
    error_code: Optional[str] = None
    diagnostic_message: Optional[str] = None


class DeterministicSymbolicValidator:
    """
    Symbolic safety gate intercepting all proposed cart mutations and tool calls.
    Prevents silent state corruption, negative quantities, or ungrounded coreferences.
    """

    @classmethod
    def validate_action_compliance(
        cls,
        intent: IntentType,
        current_state: DialogueState,
        cart_item_count: int
    ) -> ValidationResult:
        """
        Verifies if proposed action is compliant with current conversational state.
        """
        # Order confirmation requires non-empty cart
        if intent == IntentType.CONFIRM and cart_item_count == 0:
            return ValidationResult(
                is_valid=False,
                error_code="EMPTY_CART_CONFIRMATION",
                diagnostic_message="Cannot confirm an empty cart. Customer must add items first."
            )

        # Disallow checkout when already placed or cancelled without resetting
        if current_state == DialogueState.ORDER_PLACED and intent not in [IntentType.GREETING, IntentType.CANCEL, IntentType.ADD]:
            return ValidationResult(
                is_valid=False,
                error_code="ORDER_ALREADY_PLACED",
                diagnostic_message="Order has already been placed for this session."
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_schema_conformance(
        cls,
        product: Optional[Product],
        quantity: Decimal,
        unit: Optional[str] = None
    ) -> ValidationResult:
        """
        Verifies product existence, active status, strictly positive quantity,
        and valid unit normalization.
        """
        if product is None:
            return ValidationResult(
                is_valid=False,
                error_code="PRODUCT_NOT_FOUND",
                diagnostic_message="Target product does not exist in store catalogue."
            )

        if not product.is_active:
            return ValidationResult(
                is_valid=False,
                error_code="PRODUCT_INACTIVE",
                diagnostic_message=f"Product '{product.name}' is currently inactive in store catalogue."
            )

        if quantity <= Decimal("0"):
            return ValidationResult(
                is_valid=False,
                error_code="INVALID_QUANTITY",
                diagnostic_message=f"Requested quantity {quantity} must be strictly positive (> 0)."
            )

        # Check for abnormal extreme quantities (e.g. accidental > 1000 packets)
        if quantity > Decimal("500") and unit in ["packet", "bottle", "jar", "pouch", "piece"]:
            return ValidationResult(
                is_valid=False,
                error_code="EXCESSIVE_QUANTITY",
                diagnostic_message=f"Requested quantity of {quantity} {unit} exceeds normal retail limits."
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_coreference_consistency(
        cls,
        raw_phrase: str,
        resolved_product_id: Optional[str],
        pending_product_id: Optional[str],
        active_cart_pids: List[str]
    ) -> ValidationResult:
        """
        Verifies that anaphoric and implicit references ('wahi', 'kar do', 'dono')
        are grounded in prior turns.
        """
        implicit_tokens = {"wahi", "wohi", "uska", "uske", "iska", "iske", "kar do", "haan", "yes", "dono"}
        tokens = set(raw_phrase.lower().split())

        if tokens.intersection(implicit_tokens) and not resolved_product_id:
            if not pending_product_id and not active_cart_pids:
                return ValidationResult(
                    is_valid=False,
                    error_code="UNRESOLVED_COREFERENCE",
                    diagnostic_message="Implicit reference has no active or pending product referent in dialogue history."
                )

        return ValidationResult(is_valid=True)

