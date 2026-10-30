"""
DukaanSaathi — Intent Recognition Service (Phase 3 Service 4)
Deterministic rule-based intent classification for kirana conversational commerce.
Recognizes: ADD, REMOVE, SET_QUANTITY, REPLACE_QUANTITY, PRICE_QUERY,
STOCK_QUERY, CONFIRM, and CANCEL.
"""

import re
from typing import Tuple, Optional
from backend.app.schemas.intelligence import IntentType

# Explicit Regex Triggers for Conversational Intents
PRICE_PATTERNS = [
    r"\bkitne\s+k[aei]\s+hai\b",
    r"\bkitna\s+rate\s+hai\b",
    r"\bprice\s+kya\s+hai\b",
    r"\bkya\s+bhaav\s+hai\b",
    r"\bhow\s+much\s+(is|for)\b",
]

STOCK_PATTERNS = [
    r"\bkitn[ao]\s+.*hai\b",
    r"\baapke\s+paas\s+kitn[ao]\b",
    r"\bstock\s+hai\s+kya\b",
    r"\bavailable\s+hai\s+kya\b",
    r"\bhow\s+many\s+.*do\s+you\s+have\b",
    r"\bin\s+stock\b",
]

CONFIRM_PATTERNS = [
    r"\bconfirm\s+(kar\s+do|karo|karna|order)\b",
    r"\bhaan\s*,?\s*(order\s+)?confirm\b",
    r"\byes\s*,?\s*confirm\b",
    r"\bplace\s+order\b",
    r"\btheek\s+hai\s*,?\s*confirm\b",
]

CANCEL_PATTERNS = [
    r"\bcancel\s+(kar\s+do|karo|order)\b",
    r"\bnahi\s+chahiye\b",
    r"\bsaara\s+hata\s+do\b",
    r"\bpoora\s+cart\s+saaf\b",
]

REMOVE_PATTERNS = [
    r"\b(.*)\s+hata\s+do\b",
    r"\b(.*)\s+nikal\s+do\b",
    r"\bremove\s+(.*)\b",
    r"\bdelete\s+(.*)\b",
]

REPLACE_PATTERNS = [
    r"\bnahi\s*,?\s*(.+)\s+kar\s+do\b",
    r"\bdo\s+nahi\s*,?\s*(.+)\b",
    r"\bchange\s+to\s+(.+)\b",
]

class IntentClassifier:
    @staticmethod
    def classify_intent(text: str, has_intra_correction: bool = False) -> Tuple[IntentType, Optional[str]]:
        """
        Classifies user intent from normalized text.
        Returns: (IntentType, extracted_target_text_or_none)
        """
        clean = text.lower().strip()

        # 1. Price Query
        for pat in PRICE_PATTERNS:
            if re.search(pat, clean):
                return IntentType.PRICE_QUERY, None

        # 2. Stock / Availability Query
        for pat in STOCK_PATTERNS:
            if re.search(pat, clean):
                return IntentType.STOCK_QUERY, None

        # 3. Order Confirmation
        for pat in CONFIRM_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CONFIRM, None

        # 4. Order Cancellation
        for pat in CANCEL_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CANCEL, None

        # 5. Remove Item
        for pat in REMOVE_PATTERNS:
            m = re.search(pat, clean)
            if m:
                target = m.group(1).strip()
                return IntentType.REMOVE, target

        # 6. Intra-utterance or multi-turn quantity correction
        if has_intra_correction:
            return IntentType.REPLACE_QUANTITY, None

        for pat in REPLACE_PATTERNS:
            m = re.search(pat, clean)
            if m:
                target = m.group(1).strip()
                return IntentType.REPLACE_QUANTITY, target

        # 7. Default to Item Addition / Order Request
        return IntentType.ADD, None

