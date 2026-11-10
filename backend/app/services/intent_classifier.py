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
CATALOG_PATTERNS = [
    r"\bwhat\s+(items|products|things|all)?\s*(are\s+there|do\s+you\s+have|in\s+(your\s+)?shop)\b",
    r"\bkya\s+kya\s+(samaan|saman|items|products|cheezein|cheez|hai)\b",
    r"\bkya\s+(samaan|saman|milta)\s+hai\b",
    r"\bdukaan\s+m[eie]n?\s+kya\s+(kya\s+)?(hai|milta)\b",
    r"\baapke\s+paas\s+kya\s+(kya\s+)?(hai|samaan|saman)\b",
    r"\b(poori|puri|full)?\s*inventory\b",
    r"\bsaara\s+samaan\b",
    r"\ball\s+products\b",
    r"\b(kitne|kaun\s+kaun\s+se)\s+brands\b",
    r"\boptions\s+(batao|dikhao|kya\s+hai|hain)\b",
    r"\b(toothpaste|namak|chini|maggi|oil|sabun|shampoo)\s+(ke|mein|me)\s+(kitne|kya\s+kya|kaun)\b",
]

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
    r"\bdo\s+you\s+have\b",
    r"\byou\s+have\b",
    r"\bhogi\s+(aapke|apke|tere|tumhare|tumhaare)\s+paas\b",
    r"\b(hai|hogi|hoga)\s+kya\s+(aapke|apke|tere|tumhare|tumhaare)\s+paas\b",
    r"\b(hai|hogi|hoga)\s+(aapke|apke|tere|tumhare|tumhaare)\s+paas\b",
    r"\b(aapke|apke|tere|tumhare|tumhaare)\s+paas\s+.*\s+(hai|hogi|hoga)\b",
    r"\bkya\s+(aapke|apke|tere|tumhare|tumhaare)\s+paas\b",
    r"\b(aapke|apke|tere|tumhare|tumhaare)\s+paas\b",
    r"\bdukaan\s*(?:mein|me|men|pe)?\s*.*\s*(hai|hogi|hoga|kya)\b",
    r"\bhogi\s+sauce\b",
    r"\b(hai|hogi|hoga|honge)\s+kya\b",
    r"\b(hogi|hoga|honge)\s*(\?|$)",
    r"\b(sauce|ketchup|chocolate|chocolates|toffee|toffees|candy|cornflakes|chocos|cereal|oats|shampoo|namak|chini|doodh|cold drink)\s+(hai|hogi|hoga|honge)\b",
    r"\b(mil\s+jayeg[ai]|mileg[ai]|rakhte\s+ho)\b",
    r"\bavailable\s+hai\b",
    r"\bis\s+.*available\b",
    r"\b(sachet|pouch)\s+(hoga|hogi|milega|hai|nahi\s+hoga|nahi\s+hai)\b",
    r"\b(kya\s+)?(bottle\s+ki\s+jagah\s+)?(sachet|pouch)\b",
    r"\b.*nahi\s+(hai|hoga|hogi|milega)?\s*(to\s+kya|kya)\b",
    r"\b(bada|chhota)\s+packet\s+(hai|hoga|milega)\b",
]

CONFIRM_PATTERNS = [
    r"\bconfirm\s*(?:kar\s+do|karo|karna|order|kijiye)?\b",
    r"\b(?:haan|theek\s+hai|yes)\s*,?\s*(?:order\s+)(?:confirm|bhej\s+do|bhejo|kar\s+do|place|submit|pakka|final)\b",
    r"\b(?:haan|theek\s+hai|yes)\s*,?\s*(?:bhej\s+do|bhejo|place\s+kar\s+do|submit\s+kar\s+do)\b",
    r"\bplace\s+(?:the\s+)?order\b",
    r"\border\s+(?:place|confirm|bhej\s+do|bhejo|kar\s+do|submit|final|pakka)\b",
    r"\b(?:order\s+)?bhej\s+do\b",
    r"\b(?:order\s+)?pack\s+kar\s+do\b",
    r"^(?:haan|ha|theek\s+hai|yes|yep|yeah|sure|ok|okay|done|bilkul|pakka|haaji|haanji|achha\s+theek\s+hai)$",
]

CHECKOUT_REQUEST_PATTERNS = [
    r"\b(give\s+(?:me\s+)?(?:the\s+)?bill|generate\s+(?:the\s+)?bill|send\s+(?:the\s+)?bill|show\s+(?:the\s+)?bill)\b",
    r"\b(?:nahi\s+)?(?:nahi\s+)?bill\b.*?\b(bana|banao|kar|karo|de|dijiye|taiyaar|ready|kitna|nikal|bhejo|bhej)\b",
    r"\b(bana|banao|kar|karo|de|dijiye|taiyaar|ready|nikal|bhejo|bhej)\b.*?\bbill\b",
    r"^\s*bill\s*(?:bana|banao|de|kar|taiyaar|ready|dijiye|bhaiya|ji)?\s*$",
    r"\bhisaab\s*(kitab)?\s*(kar\s+do|karo|batao|bata\s+do|kitna\s+hua|bana\s+do|de\s+do)\b",
    r"\bbas\s+(itna\s+hi|ho\s+gaya|khatam)\b",
    r"\baur\s+kuch\s+nahi(\s+chahiye)?\b",
    r"\bkuch\s+aur\s+nahi(\s+chahiye)?\b",
    r"\b(nahi\s+)?aur\s+kuch\s+nahi\b",
    r"^(samaan\s+)?pack\s+(kar\s+do|karo|kijiye)\b",
    r"\bfinalize\s+(kar\s+do|karo|order)\b",
    r"\bthat('s|s)?\s+all\b",
    r"\bnothing\s+else\b",
    r"\bcheckout\b",
]

CANCEL_PATTERNS = [
    r"^(?:order\s+)?cancel\s*(?:kar\s+do|karo|order|kijiye)?$",
    r"^(?:mujhe\s+)?(?:kuch\s+bhi\s+|kuch\s+)?nahi\s+chahiye$",
    r"\b(meri\s+|mera\s+|saara\s+|poora\s+|poori\s+)?cart\s*(ko\s+)?(khali|clear|empty|saaf)\s*(kar\s+do|karo|dijiye)?\b",
    r"\b(cart\s+)?(khali|clear|empty|saaf)\s+kar\s*(do|dijiye|karo)\b",
    r"\b(sab|saara|saara\s+samaan|sab\s+kuch)\s+(hata\s+do|nikal\s+do|khali\s+kar\s+do)\b",
    r"\b(khali|clear|empty)\s+(my\s+)?cart\b",
    r"\b(empty|clear)\s+(my\s+)?cart\b",
    r"^band\s+kar\s+do$",
    r"^start\s+over$",
    r"^reset\s+(?:cart|order)$",
]

CART_QUERY_PATTERNS = [
    r"^\s*(?:ek\s+baar\s+)?check\s+(?:kar\s+do|karo|kar\s+dijiye|karna|kijiye)\s*$",
    r"^\s*check\s*$",
    r"\b(kya\s+tumne|kya\s+tune|kya\s+aapne)\s+.*\s+(add\s+kiya|add\s+kar\s+diya|add\s+kar\s+di|daala|daal\s+diya)\b",
    r"\b(cart|card|काट|कार्ट|parchi|पर्ची)\b.*\b(check|kya|pada|dikhao|batao|dekho|hai)\b",
    r"\b(usmein|cart\s+mein|card\s+mein)\s+kuch\s+pada\b",
    r"\b(abhi\s+tak\s+kya|kya\s+kya\s+add\s+hua|mera\s+order\s+kya\s+hai)\b",
    r"\b(meri\s+|mera\s+)?cart\s*(mein|me)\s*(kya|kya\s+kya)\s*(hai|daala|add\s+hua)\b",
    r"\b(kya\s+kya|kya)\s+(add\s+hua|daala\s+gaya|jud\s+gaya)\s*(hai)?\b",
    r"\b(meri\s+|mera\s+)?cart\s*(ko\s+)?(check|dekho|batao|dikhana|dikhao|dekhna\s+hai)\b",
    r"\bcart\s*check\s*(karke\s+bata[on]|karo|karna)?\b",
    r"\busm[eie]n?\s+(kuch\s+)?(hai|pada\s+hai|pada\s+hua|daala|rakha)\s*(kya)?\b",
    r"\bkuch\s+pada\s+(hua\s+)?hai\s*(kya)?\b",
    r"\bpehle\s+se\s+kuch\s+(hai|pada)\b",
    r"\bshow\s+(my\s+)?cart\b",
    r"\bwhat('s|s|\s+is)\s+in\s+my\s+cart\b",
    r"\bcart\s+(items|status)\b",
    r"\b(total|kul)\s*(kitna|kitne)\s*(hua|paise|rupaye|bana)\b",
    r"\bkitne\s*(paise|rupaye)\s*(hue|bana|lage)\b",
    r"\bkitna\s*kharcha\s*(hua|bana)\b",
    r"\bbill\s*kitna\s*(hua|bana)\b",
]
VIEW_CART_PATTERNS = CART_QUERY_PATTERNS

STORE_INFO_PATTERNS = [
    r"\b(dukaan|dukan|store|shop)\s*(kab|kitne\s+baje)\s*(khulti|khulta|band|open|close)\b",
    r"\b(dukaan|dukan|store|shop)\s*(timing|time|samay)\b",
    r"\b(dukaan|dukan|store|shop)\s*(kahan|kidhar|address|pata|location)\b",
    r"\b(home\s+)?delivery\s*(karte\s+ho|hoti\s+hai|milegi|hogi|ho\s+jayegi)\b",
    r"\b(online\s+)?payment\s*(kaise|karna|hoga|chalega|accept)\b",
    r"\b(upi|gpay|paytm|phonepe|qr\s*code|cash)\s*(chalega|lete\s+ho|hoga)\b",
    r"\b(madad|help)\s*(chahiye)?\b",
    r"\baap\s+kya\s+kar\s+sakte\s+ho\b",
]

GREETING_PATTERNS = [
    r"^(?:namaste|namaskar|hello|hi|hey|pranam|ram\s*ram|radhe\s*radhe)\b",
    r"^(?:good\s*morning|good\s*afternoon|good\s*evening)\b",
]

CHITCHAT_PATTERNS = [
    r"\b(?:kaise\s+ho|kya\s+haal\s+hai|sab\s+theek|aap\s+kaise\s+hain|how\s+are\s+you)\b",
    r"\b(?:aap\s+kaun\s+h[oain]+|who\s+are\s+you|tum\s+kaun\s+ho)\b",
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
    r"\b(\d+(?:\.\d+)?|ek|do|teen|chaar|paanch|panch|aadha)\s*(?:kg|kilo|gram|gm|packet|pack|bottle|litre|l|jar|pouch)?\s*nahi\s*,?\s*(\d+(?:\.\d+)?|ek|do|teen|chaar|paanch|panch|aadha|\w+)",
    r"\b(\d+|ek|do|teen|chaar|paanch|panch)\s+chahiye\s*,?\s*(\d+|ek|do|teen|chaar|paanch|panch)\s+nahi\b",
    r"\b(\d+(?:\.\d+)?|ek|do|teen|chaar|paanch|panch|aadha)\s*(?:kg|kilo|gram|gm|packet|pack|bottle|litre|l|jar|pouch)?\s*(?:ki\s+jagah|k\s+badle)\s*(\d+(?:\.\d+)?|ek|do|teen|chaar|paanch|panch|aadha|\w+)",
    r"\b(ek|do|\d+)?\s*(?:packet|bottle|kilo|kg|jar)?\s*(kam\s+kar\s+do|ghata\s+do|kam\s+karo|nikal\s+do|kam\s+kar\s+dijiye|kam\s+kijiye)\b",
    r"\b(ek|do|\d+)?\s*(?:packet|bottle|kilo|kg|jar)?\s*(hata\s+do|hata\s+dijiye|nikal\s+dijiye)\b",
    r"\b(quantity|qty)\s*(kam|change|badal|ghata)\s+kar\s+do\b",
    r"\bchhota\s+packet\s+kar\s+do\b",
    r"^\s*(?:bhaiya|please|arre)?\s*(\d+|ek|do|teen|chaar|paanch|panch)\s*(?:packet|bottle|kilo|kg|jar|pouch|piece)?\s*(?:kar\s+do|kar\s+dijiye|chahiye)\s*$",
]

class IntentClassifier:
    @staticmethod
    def classify_intent(
        text: str,
        has_intra_correction: bool = False,
        is_awaiting_confirmation: bool = False
    ) -> Tuple[IntentType, Optional[str]]:
        """
        Classifies user intent from normalized text.
        Returns: (IntentType, extracted_target_text_or_none)
        """
        clean = text.lower().strip()

        # Context-aware confirmation if the session was explicitly waiting for confirmation
        if is_awaiting_confirmation:
            # If the user is modifying quantity or specifying an item, allow item parsing
            has_item_spec = bool(re.search(r"\b(\d+|ek|do|teen|char|paanch|aadha)\s+(kilo|kg|packet|pack|jar|litre|liter|gm|gram|piece|bottl[e]?|darjan)\b", clean))
            if not has_item_spec:
                # Check for affirmative answers
                affirmative_words = [
                    "haan", "ha", "yes", "yep", "yeah", "theek hai", "sure", "ok", "okay",
                    "done", "bilkul", "pakka", "haaji", "haanji", "kar do", "bhej do", "bhejo",
                    "pack kar do", "order bhej do", "order kar do", "order place", "place order",
                    "confirm", "chalo", "sahi hai"
                ]
                if any(w in clean for w in affirmative_words) or clean in affirmative_words:
                    return IntentType.CONFIRM, "confirm_order"

            # Check for cancellation while awaiting confirmation
            if any(w in clean for w in ["nahi", "cancel", "mat karo", "ruko", "ab nahi", "no", "don't", "stop"]):
                return IntentType.CANCEL, None

        # 0. Checkout / Bill Summary Request ("bill bana do", "aur kuch nahi chahiye, bill bana do", "bas itna hi")
        for pat in CHECKOUT_REQUEST_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CONFIRM, "request_bill"

        # 0.1 Cart Cancellation / Clear Cart Request ("meri cart khali kar do", "cart clear kar do")
        for pat in CANCEL_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CANCEL, None

        # 0.1 View Cart / Cart Query Request
        for pat in CART_QUERY_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CART_QUERY, None

        # 0.2 Store Information / Hours / Address / Delivery
        for pat in STORE_INFO_PATTERNS:
            if re.search(pat, clean):
                return IntentType.STORE_INFO, None

        # 0.3 Catalog / Shop Inventory Inquiry
        for pat in CATALOG_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CATALOG_QUERY, None

        # 0.4 Greeting & Chitchat Short-Circuit
        has_item_or_qty = bool(re.search(r"\b(packet|pack|kilo|kg|litre|liter|gm|gram|chahiye|dena|daal|kar\s+do|bhejo)\b", clean))
        if not has_item_or_qty:
            for pat in GREETING_PATTERNS:
                if re.search(pat, clean):
                    return IntentType.GREETING, None
            for pat in CHITCHAT_PATTERNS:
                if re.search(pat, clean):
                    return IntentType.CHITCHAT, None

        # 1. Price Query
        for pat in PRICE_PATTERNS:
            if re.search(pat, clean):
                return IntentType.PRICE_QUERY, None

        # 2. Stock / Availability Query (only if user is not explicitly requesting to add/pack into cart)
        has_order_verb = bool(re.search(
            r"\b(pack\s+(?:kar\s+do|kar\s+dijiye|karo)|add\s+(?:kar\s+do|kar\s+dijiye|karo)|cart\s+m[eie]n?\s+(?:add|pack|daal|kar)|(?:kar\s+do|kar\s+dijiye)\s*(?:cart\s+m[eie]n?)?|de\s+do\s+cart|daal\s+(?:do|dijiye))\b",
            clean
        ))
        if not has_order_verb:
            for pat in STOCK_PATTERNS:
                if re.search(pat, clean):
                    return IntentType.STOCK_QUERY, None

        # 3. Order Confirmation
        for pat in CONFIRM_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CONFIRM, "confirm_order"

        # 4. Remove Item
        for pat in REMOVE_PATTERNS:
            m = re.search(pat, clean)
            if m:
                target = m.group(1).strip()
                return IntentType.REMOVE, target

        # 6. Intra-utterance or multi-turn quantity correction
        if any(w in clean for w in ["dono", "donon", "both"]):
            return IntentType.ADD, None

        if has_intra_correction:
            return IntentType.REPLACE_QUANTITY, None

        for pat in REPLACE_PATTERNS:
            m = re.search(pat, clean)
            if m:
                target = m.group(1).strip()
                return IntentType.REPLACE_QUANTITY, target

        # 7. Default to Item Addition / Order Request
        return IntentType.ADD, None

