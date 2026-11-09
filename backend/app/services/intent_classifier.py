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

CHECKOUT_REQUEST_PATTERNS = [
    r"\bbill\s+(bana\s+do|banao|kar\s+do|karo|de\s+do|kitna\s+hua)\b",
    r"\bhisaab\s*(kitab)?\s*(kar\s+do|karo|batao|bata\s+do|kitna\s+hua)\b",
    r"\bbas\s+(itna\s+hi|ho\s+gaya|khatam)\b",
    r"\baur\s+kuch\s+nahi(\s+chahiye)?\b",
    r"\bkuch\s+aur\s+nahi(\s+chahiye)?\b",
    r"\bpack\s+(kar\s+do|karo)\b",
    r"\bfinalize\s+(kar\s+do|karo|order)\b",
    r"\bthat('s|s)?\s+all\b",
    r"\bnothing\s+else\b",
]

CANCEL_PATTERNS = [
    r"^(order\s+)?cancel\s*(kar\s+do|karo|order)?$",
    r"^(kuch\s+bhi\s+)?nahi\s+chahiye$",
    r"^(saara|poora)\s+(cart\s+)?(hata\s+do|saaf\s+kar\s+do|khali\s+kar\s+do)$",
    r"^band\s+kar\s+do$"
]

REMOVE_PATTERNS = [
    r"\b(.*)\s+hata\s+do\b",
    r"\b(.*)\s+nikal\s+do\b",
    r"\bremove\s+(.*)\b",
    r"\bdelete\s+(.*)\b",
    r"\b(.*)\s+(nahi\s+chahiye|mat\s+daalna|mat\s+do)\b",
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
                return IntentType.CONFIRM, "confirm_order"

        # 3.5 Checkout / Bill Summary Request ("bill bana do", "aur kuch nahi chahiye", "bas itna hi")
        for pat in CHECKOUT_REQUEST_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CONFIRM, "request_bill"

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

