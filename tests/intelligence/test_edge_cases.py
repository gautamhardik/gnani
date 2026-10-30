"""
DukaanSaathi — Edge Case & Robustness Test Suite
Validates boundary behaviors: mixed language, uncatalogued items, Hindi numerals,
fractional units, and ambiguous queries.
"""

from decimal import Decimal
import pytest
from backend.app.services.conversation_manager import ConversationManager
from backend.app.schemas.intelligence import DialogueState, ClarificationType

def test_exotic_unsupported_product_no_hallucination(db_session):
    manager = ConversationManager(db_session)
    res = manager.process_turn(
        session_id="SESS_EDGE_01",
        user_utterance="Mujhe ek kilo avocado chahiye."
    )
    assert res.state == DialogueState.NEEDS_CLARIFICATION
    assert res.action.action == "product_not_found"
    assert len(res.cart) == 0

def test_hindi_fractional_weight_loose_sugar(db_session):
    manager = ConversationManager(db_session)
    res = manager.process_turn(
        session_id="SESS_EDGE_02",
        user_utterance="Pao kilo chini dena."
    )
    assert res.action.action == "add_items"
    assert len(res.cart) == 1
    assert res.cart[0].product_id == "PRD034"
    assert res.cart[0].quantity == Decimal("0.25")

def test_intra_utterance_self_correction_multi_numeral(db_session):
    manager = ConversationManager(db_session)
    res = manager.process_turn(
        session_id="SESS_EDGE_03",
        user_utterance="Ek packet Maggi... nahi teen packet kar do."
    )
    assert res.action.action == "replace_quantity"
    assert len(res.cart) == 1
    assert res.cart[0].product_id == "PRD041"
    assert res.cart[0].quantity == Decimal("3")

def test_generic_milk_multiple_turns_preserves_cart(db_session):
    manager = ConversationManager(db_session)
    # Turn 1: Add flour
    res1 = manager.process_turn(
        session_id="SESS_EDGE_04",
        user_utterance="Ek kilo aata de do."
    )
    assert len(res1.cart) == 1

    # Turn 2: Ambiguous milk query
    res2 = manager.process_turn(
        session_id="SESS_EDGE_04",
        user_utterance="Aur ek doodh dena.",
        existing_cart=[it.model_dump() for it in res1.cart]
    )
    assert res2.action.action == "clarify_product"
    # Cart still has flour!
    assert len(res2.cart) == 1
    assert res2.cart[0].product_id == "PRD001"

    # Turn 3: Clarify variant
    res3 = manager.process_turn(
        session_id="SESS_EDGE_04",
        user_utterance="Amul Gold aadha litre.",
        existing_cart=[it.model_dump() for it in res2.cart]
    )
    assert res3.action.action == "add_items"
    assert len(res3.cart) == 2
    pids = {it.product_id for it in res3.cart}
    assert "PRD001" in pids
    assert "PRD022" in pids

