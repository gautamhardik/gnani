"""
DukaanSaathi — Test Suite for Intent Recognition Service (Service 4)
Tests classification of ADD, REMOVE, REPLACE_QUANTITY, PRICE_QUERY,
STOCK_QUERY, CONFIRM, and CANCEL.
"""

from backend.app.services.intent_classifier import IntentClassifier
from backend.app.schemas.intelligence import IntentType

def test_price_query_intent():
    queries = [
        "Chini kitne ki hai?",
        "Maggi price kya hai?",
        "Atta ka kya bhaav hai?",
        "How much is Amul milk?",
    ]
    for q in queries:
        intent, _ = IntentClassifier.classify_intent(q)
        assert intent == IntentType.PRICE_QUERY, f"Failed for '{q}', got {intent}"

def test_stock_query_intent():
    queries = [
        "Amul doodh available hai kya?",
        "Aapke paas kitna ghee bacha hai?",
        "Maggi in stock?",
    ]
    for q in queries:
        intent, _ = IntentClassifier.classify_intent(q)
        assert intent == IntentType.STOCK_QUERY, f"Failed for '{q}', got {intent}"

def test_confirm_intent():
    queries = [
        "Haan confirm kar do",
        "Theek hai, confirm",
        "Order confirm karo",
        "Place order",
    ]
    for q in queries:
        intent, _ = IntentClassifier.classify_intent(q)
        assert intent == IntentType.CONFIRM, f"Failed for '{q}', got {intent}"

def test_cancel_intent():
    queries = [
        "Cancel kar do",
        "Nahi chahiye",
        "Saara hata do",
        "Poora cart saaf kar do",
    ]
    for q in queries:
        intent, _ = IntentClassifier.classify_intent(q)
        assert intent == IntentType.CANCEL, f"Failed for '{q}', got {intent}"

def test_remove_intent():
    queries = [
        ("Maggi hata do", "maggi"),
        ("Chini nikal do", "chini"),
        ("Remove Parle-G", "parle-g"),
    ]
    for q, expected_target in queries:
        intent, target = IntentClassifier.classify_intent(q)
        assert intent == IntentType.REMOVE, f"Failed for '{q}', got {intent}"
        assert expected_target.lower() in target.lower()

def test_replace_quantity_intent():
    queries = [
        "Nahi, aadha kilo kar do",
        "Do nahi, teen kar do",
        "Change to 2 packets",
    ]
    for q in queries:
        intent, _ = IntentClassifier.classify_intent(q)
        assert intent == IntentType.REPLACE_QUANTITY, f"Failed for '{q}', got {intent}"

def test_add_intent_default():
    queries = [
        "Mujhe ek kilo aata chahiye",
        "Do packet Maggi dena",
        "Ek litre tel add kar do",
    ]
    for q in queries:
        intent, _ = IntentClassifier.classify_intent(q)
        assert intent == IntentType.ADD, f"Failed for '{q}', got {intent}"
