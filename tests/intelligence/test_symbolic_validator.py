"""
Unit tests for Deterministic Symbolic Validator (ReacTOD).
"""

from decimal import Decimal
import pytest

from backend.app.services.symbolic_validator import (
    DeterministicSymbolicValidator,
    ValidationResult
)
from backend.app.schemas.intelligence import DialogueState, IntentType
from backend.app.models import Product


def test_action_compliance_rejects_empty_cart_confirmation():
    res = DeterministicSymbolicValidator.validate_action_compliance(
        intent=IntentType.CONFIRM,
        current_state=DialogueState.COLLECTING,
        cart_item_count=0
    )
    assert res.is_valid is False
    assert res.error_code == "EMPTY_CART_CONFIRMATION"


def test_action_compliance_permits_populated_cart_confirmation():
    res = DeterministicSymbolicValidator.validate_action_compliance(
        intent=IntentType.CONFIRM,
        current_state=DialogueState.COLLECTING,
        cart_item_count=3
    )
    assert res.is_valid is True


def test_schema_conformance_rejects_negative_or_zero_quantity():
    dummy_prod = Product(
        product_id="PRD999",
        name="Test Item",
        is_active=True,
        price_inr=Decimal("50")
    )
    res_zero = DeterministicSymbolicValidator.validate_schema_conformance(
        product=dummy_prod,
        quantity=Decimal("0"),
        unit="packet"
    )
    assert res_zero.is_valid is False
    assert res_zero.error_code == "INVALID_QUANTITY"

    res_neg = DeterministicSymbolicValidator.validate_schema_conformance(
        product=dummy_prod,
        quantity=Decimal("-2"),
        unit="packet"
    )
    assert res_neg.is_valid is False
    assert res_neg.error_code == "INVALID_QUANTITY"


def test_schema_conformance_rejects_inactive_product():
    inactive_prod = Product(
        product_id="PRD998",
        name="Discontinued Item",
        is_active=False,
        price_inr=Decimal("100")
    )
    res = DeterministicSymbolicValidator.validate_schema_conformance(
        product=inactive_prod,
        quantity=Decimal("1"),
        unit="packet"
    )
    assert res.is_valid is False
    assert res.error_code == "PRODUCT_INACTIVE"


def test_coreference_consistency_detects_ungrounded_anaphora():
    res_ungrounded = DeterministicSymbolicValidator.validate_coreference_consistency(
        raw_phrase="haan wahi pack kar do",
        resolved_product_id=None,
        pending_product_id=None,
        active_cart_pids=[]
    )
    assert res_ungrounded.is_valid is False
    assert res_ungrounded.error_code == "UNRESOLVED_COREFERENCE"

    res_grounded = DeterministicSymbolicValidator.validate_coreference_consistency(
        raw_phrase="haan wahi pack kar do",
        resolved_product_id=None,
        pending_product_id="PRD001",
        active_cart_pids=[]
    )
    assert res_grounded.is_valid is True

