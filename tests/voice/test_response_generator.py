"""
Unit tests for Assistant Response Generator (Phase 4 Task 6).
"""

from decimal import Decimal
import pytest

from backend.app.schemas.intelligence import (
    DialogueState,
    IntentType,
    TurnResponse,
    TurnAction,
    CartItem,
    ClarificationType,
)
from backend.app.services.response_generator import AssistantResponseGenerator


def test_empty_speech_repetition_prompt():
    turn = TurnResponse(
        session_id="SESS_TEST",
        intent=IntentType.UNKNOWN,
        state=DialogueState.COLLECTING,
        action=TurnAction(action="prompt_repeat", message=""),
        cart=[],
        total_amount=Decimal("0.00"),
        spoken_response=""
    )
    resp = AssistantResponseGenerator.generate_response(turn, raw_transcript="")
    assert "Kripya dobara boliye" in resp


def test_add_items_response():
    item1 = CartItem(
        product_id="PRD034",
        name="Loose Sugar",
        quantity=Decimal("1.0"),
        unit="kg",
        unit_price=Decimal("42.00"),
        subtotal=Decimal("42.00")
    )
    item2 = CartItem(
        product_id="PRD041",
        name="Maggi 2-Minute Masala Noodles",
        quantity=Decimal("2.0"),
        unit="packet",
        unit_price=Decimal("14.00"),
        subtotal=Decimal("28.00")
    )
    turn = TurnResponse(
        session_id="SESS_TEST",
        intent=IntentType.ADD,
        state=DialogueState.COLLECTING,
        action=TurnAction(action="add_items", items=[item1, item2], message=""),
        cart=[item1, item2],
        total_amount=Decimal("70.00"),
        spoken_response=""
    )
    resp = AssistantResponseGenerator.generate_response(turn, raw_transcript="Ek kilo chini aur do packet Maggi dena")
    assert "Ji bhaiya" in resp
    assert "Loose Sugar" in resp or "chini" in resp.lower() or "add kar diye hain" in resp
    assert "70 rupaye" in resp


def test_replace_quantity_response():
    item = CartItem(
        product_id="PRD034",
        name="Loose Sugar",
        quantity=Decimal("0.5"),
        unit="kg",
        unit_price=Decimal("42.00"),
        subtotal=Decimal("21.00")
    )
    turn = TurnResponse(
        session_id="SESS_TEST",
        intent=IntentType.REPLACE_QUANTITY,
        state=DialogueState.COLLECTING,
        action=TurnAction(action="replace_quantity", items=[item], message=""),
        cart=[item],
        total_amount=Decimal("21.00"),
        spoken_response=""
    )
    resp = AssistantResponseGenerator.generate_response(turn, raw_transcript="Aadha kilo kar do")
    assert "aadha kilo" in resp
    assert "21 rupaye" in resp


def test_clarify_product_options():
    turn = TurnResponse(
        session_id="SESS_TEST",
        intent=IntentType.ADD,
        state=DialogueState.NEEDS_CLARIFICATION,
        action=TurnAction(
            action="clarify_product",
            clarification_type=ClarificationType.PRODUCT,
            clarification_options=["Amul Taaza", "Amul Gold", "Mother Dairy Classic"],
            message=""
        ),
        cart=[],
        total_amount=Decimal("0.00"),
        spoken_response=""
    )
    resp = AssistantResponseGenerator.generate_response(turn, raw_transcript="Ek doodh dena")
    assert "Amul Taaza" in resp
    assert "Amul Gold" in resp
    assert "Mother Dairy Classic" in resp


def test_stock_boundary_insufficient_stock():
    turn = TurnResponse(
        session_id="SESS_TEST",
        intent=IntentType.ADD,
        state=DialogueState.NEEDS_CLARIFICATION,
        action=TurnAction(
            action="check_stock",
            stock_quote=Decimal("7"),
            message="Only 7 available"
        ),
        cart=[],
        total_amount=Decimal("0.00"),
        spoken_response=""
    )
    resp = AssistantResponseGenerator.generate_response(turn, raw_transcript="Das ghee jar de do")
    assert "7 available" in resp or "sirf 7" in resp
    assert "Kya 7" in resp or "7 kar dein" in resp


def test_order_confirmation_response():
    turn = TurnResponse(
        session_id="SESS_TEST",
        intent=IntentType.CONFIRM,
        state=DialogueState.ORDER_PLACED,
        action=TurnAction(action="confirm_existing_cart", message=""),
        cart=[],
        total_amount=Decimal("150.00"),
        spoken_response=""
    )
    resp = AssistantResponseGenerator.generate_response(turn, raw_transcript="Haan, order confirm kar do")
    assert "confirm ho gaya" in resp
    assert "150 rupaye" in resp
