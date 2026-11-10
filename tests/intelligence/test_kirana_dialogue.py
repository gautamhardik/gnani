"""
DukaanSaathi — Real-World Bharat Kirana Dialogue Test Suite
Tests:
1. Missing-quantity prompting for bare product requests (e.g. 'Cheeni chahiye').
2. Context carryover on subsequent quantity utterance (e.g. 'Do kilo' completes addition).
3. Rupee-denomination requests (e.g. '23 rupaye ki cheeni' -> 0.5 kg).
4. Generic category disambiguation with stock sorting (e.g. 'tel', 'biscuit', 'sabun').
5. Checkout completion transitions ('aur kuch nahi chahiye, bill bana do' -> AWAITING_CONFIRMATION without cart wipe).
6. Price and Stock query carryover.
"""

from decimal import Decimal
import pytest

from backend.app.services.conversation_manager import ConversationManager
from backend.app.schemas.intelligence import DialogueState, IntentType, ClarificationType


def test_missing_quantity_prompt_and_context_carryover(db_session):
    manager = ConversationManager(db_session)
    session_id = "SESS_KIRANA_001"

    # Turn 1: Bare product mention without quantity
    res1 = manager.process_turn(session_id, "Cheeni chahiye", existing_cart=[])
    assert res1.state == DialogueState.NEEDS_CLARIFICATION
    assert res1.action.action == "clarify_quantity"
    assert res1.action.clarification_type == ClarificationType.QUANTITY
    assert "₹46" in res1.action.message or "46" in res1.action.message
    assert "Loose Sugar" in res1.action.message
    assert len(res1.cart) == 0

    # Turn 2: Customer specifies quantity
    res2 = manager.process_turn(session_id, "Do kilo de do", existing_cart=[])
    assert res2.state == DialogueState.COLLECTING
    assert res2.action.action == "add_items"
    assert len(res2.cart) == 1
    assert res2.cart[0].product_id == "PRD034"
    assert res2.cart[0].quantity == Decimal("2")
    assert res2.cart[0].unit == "kg"
    assert res2.total_amount == Decimal("92.00")
    assert "Aur kya chahiye bhaiya?" in res2.spoken_response


def test_rupee_denomination_request(db_session):
    manager = ConversationManager(db_session)
    session_id = "SESS_KIRANA_002"

    # Loose Sugar is ₹46/kg -> 23 rupees should yield exactly 0.5 kg
    res = manager.process_turn(session_id, "23 rupaye ki cheeni de do", existing_cart=[])
    assert res.state == DialogueState.COLLECTING
    assert res.action.action == "add_items"
    assert len(res.cart) == 1
    assert res.cart[0].product_id == "PRD034"
    assert res.cart[0].quantity == Decimal("0.5")
    assert res.cart[0].unit == "kg"
    assert res.cart[0].subtotal == Decimal("23.00")


def test_generic_category_disambiguation_oil_and_biscuit(db_session):
    manager = ConversationManager(db_session)

    # 1. 'tel' / 'cooking oil' has multiple options -> must clarify product
    res_oil = manager.match_product = manager.matcher.match_product("cooking oil")
    assert res_oil.is_ambiguous is True
    assert res_oil.clarification_type == ClarificationType.PRODUCT
    assert len(res_oil.candidates) >= 2
    assert any("Sunflower" in c.name for c in res_oil.candidates)
    assert any("Mustard" in c.name for c in res_oil.candidates)

    # 2. 'biscuit' has multiple options
    res_biscuit = manager.matcher.match_product("biscuit")
    assert res_biscuit.is_ambiguous is True
    assert len(res_biscuit.candidates) >= 3
    assert any("Parle-G" in c.name for c in res_biscuit.candidates)
    assert any("Good Day" in c.name for c in res_biscuit.candidates)

    # 3. 'toothpaste' has single option (Colgate)
    res_paste = manager.matcher.match_product("toothpaste")
    assert res_paste.matched is True
    assert "Colgate" in res_paste.product.name


def test_checkout_completion_does_not_wipe_cart(db_session):
    manager = ConversationManager(db_session)
    session_id = "SESS_KIRANA_003"

    existing_cart = [{
        "product_id": "PRD034",
        "name": "Loose Sugar",
        "quantity": 1,
        "unit": "kg",
        "unit_price": 46.0,
        "subtotal": 46.0
    }]

    # Customer finishes shopping: "Aur kuch nahi chahiye, bill bana do"
    res = manager.process_turn(
        session_id=session_id,
        user_utterance="Aur kuch nahi chahiye, bill bana do",
        existing_cart=existing_cart
    )
    assert res.state == DialogueState.AWAITING_CONFIRMATION
    assert res.action.action == "awaiting_confirmation"
    assert len(res.cart) == 1
    assert res.total_amount == Decimal("46.00")
    assert "Aapka bill 1 items ke liye" in res.action.message

    # Customer confirms
    res_confirm = manager.process_turn(
        session_id=session_id,
        user_utterance="Haan confirm kar do",
        existing_cart=[it.model_dump() for it in res.cart]
    )
    assert res_confirm.state == DialogueState.ORDER_PLACED
    assert res_confirm.action.action == "confirm_existing_cart"
    assert len(res_confirm.cart) == 1


def test_price_query_carryover(db_session):
    manager = ConversationManager(db_session)
    session_id = "SESS_KIRANA_004"

    # Turn 1: Price query
    res1 = manager.process_turn(session_id, "Cheeni kitne ki hai?", existing_cart=[])
    assert res1.action.action == "quote_price"
    assert res1.action.price_quote == Decimal("46.00")

    # Turn 2: Follow-up quantity adds the queried item
    res2 = manager.process_turn(session_id, "Ek kilo de do", existing_cart=[])
    assert res2.action.action == "add_items"
    assert len(res2.cart) == 1
    assert res2.cart[0].product_id == "PRD034"
    assert res2.cart[0].quantity == Decimal("1")

