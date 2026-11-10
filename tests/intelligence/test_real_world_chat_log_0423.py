"""
DukaanSaathi — Real-World Chat Log Regression Verification (04:23 AM Session)
Replays the exact failure log sequence to verify:
1. Cart query / inspection with ASR homophone 'card check'
2. Pack-weight auto-calculation: 1 kg requested for 250 g Tata Tea -> 4 packets (₹500)
3. Intra-utterance negation & correction: 'ek packet nahi, ek kilo bola maine' -> retains/sets 4 packets
4. Contextual pending quantity slot lock: 'hair oil' -> 'ek bottle' -> 1 bottle Dabur Amla Hair Oil (no soda/cold drink)
5. Multi-script Gurmukhi parsing: 'Battery' -> 'ਦੋ pack' -> 2 packs Eveready AA Battery (no mosquito coils)
6. Bare unit defaulting: 'Sugar' -> 'kilo add kar do' -> 1 kg Loose Sugar (no wheat flour)
"""

from decimal import Decimal
import pytest
from backend.app.schemas.intelligence import IntentType, DialogueState
from backend.app.services.conversation_manager import ConversationManager

def test_real_world_chat_log_0423(db_session):
    mgr = ConversationManager(db=db_session, store_id="STORE001")
    session_id = "test_sess_0423_regression"
    cart = []

    # 1. User: "card check करके बताना, उसमें कुछ पड़ा हुआ है क्या पहले से?"
    res1 = mgr.process_turn(session_id, "card check करके बताना, उसमें कुछ पड़ा हुआ है क्या पहले से?", existing_cart=cart)
    assert res1.intent in [IntentType.CART_QUERY, IntentType.VIEW_CART]
    assert "khali" in res1.spoken_response.lower()
    assert "product_not_found" not in (res1.action.action if res1.action else "")
    assert len(res1.cart) == 0

    # 2. User: "चाय पत्ती है तुम्हारे पास?"
    res2 = mgr.process_turn(session_id, "चाय पत्ती है तुम्हारे पास?", existing_cart=cart)
    assert res2.intent == IntentType.STOCK_QUERY
    assert "Tata Tea Premium 250 g" in res2.spoken_response
    assert "kitna chahiye" in res2.spoken_response.lower()

    # 3. User: "एक किलो कर दो।" -> Should calculate 1000g / 250g = 4 packets (₹500)
    res3 = mgr.process_turn(session_id, "एक किलो कर दो।", existing_cart=cart)
    assert res3.intent == IntentType.ADD
    assert len(res3.cart) == 1
    tea_item = res3.cart[0]
    assert tea_item.name == "Tata Tea Premium 250 g"
    assert tea_item.quantity == Decimal("4")
    assert tea_item.unit == "packet"
    assert res3.total_amount == Decimal("500.00")
    cart = [it.dict() if hasattr(it, "dict") else it.model_dump() for it in res3.cart]

    # 4. User: "एक packet नहीं, एक किलो बोला मैंने।" -> Negation stripping & maintaining 4 packets
    res4 = mgr.process_turn(session_id, "एक packet नहीं, एक किलो बोला मैंने।", existing_cart=cart)
    assert res4.intent in [IntentType.REPLACE_QUANTITY, IntentType.ADD]
    assert len(res4.cart) == 1
    tea_item_updated = res4.cart[0]
    assert tea_item_updated.name == "Tata Tea Premium 250 g"
    assert tea_item_updated.quantity == Decimal("4")
    assert tea_item_updated.unit == "packet"
    assert res4.total_amount == Decimal("500.00")
    cart = [it.dict() if hasattr(it, "dict") else it.model_dump() for it in res4.cart]

    # 5. User: "hair oil" -> asks quantity for Dabur Amla Hair Oil
    res5a = mgr.process_turn(session_id, "hair oil", existing_cart=cart)
    assert res5a.intent in [IntentType.STOCK_QUERY, IntentType.ADD]
    assert "Dabur Amla Hair Oil 100 ml" in res5a.spoken_response
    assert "kitna chahiye" in res5a.spoken_response.lower()

    # User: "एक bottle।" -> Adds 1 bottle of Dabur Amla Hair Oil (NEVER Sprite/Coca-Cola!)
    res5b = mgr.process_turn(session_id, "एक bottle।", existing_cart=cart)
    assert res5b.intent == IntentType.ADD
    oil_item = next((it for it in res5b.cart if "Dabur Amla" in it.name), None)
    assert oil_item is not None
    assert oil_item.quantity == Decimal("1")
    assert oil_item.unit == "bottle"
    # Sprite or Coke must NEVER be in cart or clarification
    assert not any("Sprite" in it.name or "Coca-Cola" in it.name for it in res5b.cart)
    cart = [it.dict() if hasattr(it, "dict") else it.model_dump() for it in res5b.cart]

    # 6. User: "Battery" -> asks quantity for Eveready AA Battery 2 pack
    res6a = mgr.process_turn(session_id, "Battery", existing_cart=cart)
    assert res6a.intent in [IntentType.STOCK_QUERY, IntentType.ADD]
    assert "Eveready AA Battery 2 pack" in res6a.spoken_response
    assert "kitna chahiye" in res6a.spoken_response.lower()

    # User: "ਦੋ pack।" (Gurmukhi 2) -> Adds 2 packs of Eveready AA Battery (NEVER Mosquito coils/Matchbox!)
    res6b = mgr.process_turn(session_id, "ਦੋ pack।", existing_cart=cart)
    assert res6b.intent == IntentType.ADD
    batt_item = next((it for it in res6b.cart if "Eveready" in it.name), None)
    assert batt_item is not None
    assert batt_item.quantity == Decimal("2")
    assert batt_item.unit == "pack"
    assert not any("Mosquito" in it.name or "Matchbox" in it.name for it in res6b.cart)
    cart = [it.dict() if hasattr(it, "dict") else it.model_dump() for it in res6b.cart]

    # 7. User: "Sugar" -> asks quantity for Loose Sugar
    res7a = mgr.process_turn(session_id, "Sugar", existing_cart=cart)
    assert res7a.intent in [IntentType.STOCK_QUERY, IntentType.ADD]
    assert "Loose Sugar" in res7a.spoken_response
    assert "kitna chahiye" in res7a.spoken_response.lower()

    # User: "किलो add कर दो।" (Bare unit defaulting to 1 kg Loose Sugar, NEVER Atta!)
    res7b = mgr.process_turn(session_id, "किलो add कर दो।", existing_cart=cart)
    assert res7b.intent == IntentType.ADD
    sugar_item = next((it for it in res7b.cart if "Sugar" in it.name), None)
    assert sugar_item is not None
    assert sugar_item.quantity == Decimal("1")
    assert sugar_item.unit == "kg"
    assert not any("Atta" in it.name for it in res7b.cart)
    cart = [it.dict() if hasattr(it, "dict") else it.model_dump() for it in res7b.cart]

    # 8. User: "मेरी cart खाली कर दो।" -> Clears cart completely
    res8 = mgr.process_turn(session_id, "मेरी cart खाली कर दो。", existing_cart=cart)
    assert res8.intent == IntentType.CANCEL
    assert len(res8.cart) == 0
    assert "khali" in res8.spoken_response.lower()
    assert res8.total_amount == Decimal("0")
