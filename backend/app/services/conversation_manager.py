"""
DukaanSaathi — Conversation Manager & Dialogue State Machine (Phase 3 Service 6)
Orchestrates normalization, product matching, quantity parsing, intent classification,
cart state, and multi-turn corrections.
"""

import re
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from backend.app.schemas.intelligence import (
    DialogueState,
    IntentType,
    ClarificationType,
    TurnAction,
    TurnResponse,
    CartItem,
    ExtractedQuantity,
)
from backend.app.services.normalizer import TranscriptNormalizer
from backend.app.services.matcher import ProductMatcher
from backend.app.services.quantity_parser import QuantityParser
from backend.app.services.intent_classifier import IntentClassifier
from backend.app.services.cart_service import CartService
from backend.app.services.inventory_service import InventoryService
from backend.app.services.symbolic_validator import DeterministicSymbolicValidator
from backend.app.models import OrderSession, Product

def clean_conversational_entity(text: str) -> str:
    """
    Strips conversational question wrappers, courtesies, and request prefixes/suffixes
    to extract the core product/brand entity.
    """
    s = text.strip()
    s = re.sub(r'^[?!.,\s]+|[?!.,\s]+$', '', s)

    patterns = [
        # Leading prefixes
        r'^(?:to\s+)?(?:jo\s+)?(?:packet|samaan|item)\s+available\s+hai\s+(?:uske|uska)\s+',
        r'^(?:do\s+you\s+have|you\s+have|can\s+i\s+get|what\s+about|is\s+there|are\s+there)\s+',
        r'^(?:kya\s+)?(?:aapke|apke|tere|aapki)\s*(?:paas|pas)?\s*(?:dukaan|dukan|store)?\s*(?:mein|me|men|pe)?\s*',
        r'^(?:dukaan|dukan|store)\s*(?:mein|me|men|pe)?\s*',
        r'^(?:kya\s+)',
        r'^(?:bhaiya|please|acha|theek\s+hai|haan|ok|ji)\s*',
        r'^(?:to\s+)?(?:\b(?:ek|do|teen|chaar|paanch|\d+)\b)\s*(?:packet|bottle|kilo|kg|jar|pouch|can)?\s*(?:ki\s+)?',
        # Trailing suffixes
        r'\s+(?:nahi|nhi)\s*(?:hai|hoga|hogi|milega|milegi)?(?:\s+to\s+kya|\s+kya)?$',
        r'\s+(?:nahi|nhi)$',
        r'\s+(?:hai|hogi|hoga|honge)\s+(?:kya)?(?:\s+(?:aapke|apke|tere)\s+paas)?$',
        r'\s+kya\s+(?:aapke|apke|tere)\s+paas$',
        r'\s+(?:hai|hogi|hoga|honge|milega|milegi|mil\s+jayega|mil\s+jayegi|rakhte\s+ho)$',
        r'\s+kya$',
        r'\s+hogi\s+.*$',
        r'\s+hoga\s+.*$',
        r'\s+hai\s+.*$',
        r'\s+(?:ki|ka|ke)?\s*(?:add\s+kar\s+dijiye|add\s+kar\s+do|kar\s+dijiye|kar\s+do|de\s+dijiye|de\s+do|daal\s+dijiye|daal\s+do|pack\s+kar\s+dijiye|pack\s+kar\s+do)\s*(?:cart\s+(?:mein|me))?$',
        r'\s+(?:ki|ka|ke)?\s*(?:cart\s+(?:mein|me))\s*(?:add\s+kar\s+dijiye|add\s+kar\s+do|kar\s+dijiye|kar\s+do|de\s+dijiye|de\s+do|daal\s+dijiye|daal\s+do|pack\s+kar\s+dijiye|pack\s+kar\s+do)?$',
        r'\s+chahiye\s+(?:mujhe|humein|humko)?$',
        r'\s+(?:mujhe|humein|humko)\s+chahiye$',
        r'\s+(?:ka|ki|ke)$',
    ]

    for _ in range(3):
        prev = s
        for p in patterns:
            s = re.sub(p, '', s, flags=re.IGNORECASE).strip()
        if s == prev:
            break

    words = s.split()
    if len(words) == 2 and words[0].lower() == words[1].lower():
        s = words[0]
    return s.strip()

def is_turn_for_pending_product(clause: str, pending_prod: Product, qty_info: ExtractedQuantity) -> bool:
    """
    Determines if user utterance is specifying a quantity/unit or affirmative order for the pending product
    rather than asking for a completely new, distinct catalogue item.
    """
    c_clean = re.sub(r"[^\w\s]", " ", clause).lower()
    words = [w for w in c_clean.split() if w]

    STOPWORDS = {
        "ek", "do", "teen", "chaar", "char", "paanch", "panch", "chhe", "che", "saat", "aath", "nau", "das",
        "aadha", "half", "one", "two", "three", "four", "five",
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "bottle", "bottles", "pack", "packs", "packet", "packets", "pkt", "pkts",
        "kilo", "kilos", "kg", "kgs", "gram", "grams", "gm", "gms", "g",
        "litre", "litres", "liter", "liters", "l", "ml", "pouch", "pouches",
        "jar", "jars", "dabba", "piece", "pieces", "can", "cans", "tin", "tins", "box", "boxes",
        "add", "kar", "karo", "kardo", "do", "de", "dena", "dijiye", "daal", "daalo", "pack", "chahiye",
        "bhaiya", "please", "haan", "theek", "acha", "ji", "to", "bhi", "ki", "ka", "ke", "ko",
        "mein", "me", "cart", "mujhe", "humein", "humko", "dena", "le", "lo", "ye", "yeh", "wahi",
        "iska", "iske", "uska", "uske", "wali", "wala", "vale", "bola", "maine", "hi"
    }

    remaining = [w for w in words if not w.isdigit() and w not in STOPWORDS]
    if not remaining:
        # Pure quantity or unit utterance e.g. "ek bottle", "do pack", "kilo add kar do", "ek kilo kar do"
        return True

    # Check if remaining tokens are descriptors of the pending product
    pending_tokens = set(re.sub(r"[^\w\s]", " ", pending_prod.name.lower()).split())
    if pending_prod.brand:
        pending_tokens.update(pending_prod.brand.lower().split())
    if pending_prod.category:
        pending_tokens.update(pending_prod.category.lower().split())

    # If remaining tokens match the pending product (e.g. "hair oil", "battery", "sugar", "tea", "clinic plus")
    if all(w in pending_tokens for w in remaining):
        return True

    return False

class ConversationManager:
    # Class-level persistent context storage across HTTP turns
    _global_session_contexts: Dict[str, Dict[str, Any]] = {}

    def __init__(self, db: Session, store_id: str = "STORE001"):
        self.db = db
        self.store_id = store_id
        self.normalizer = TranscriptNormalizer()
        self.matcher = ProductMatcher(db, store_id=store_id)
        self.inventory_service = InventoryService(db)
        self.session_contexts = ConversationManager._global_session_contexts

    def process_turn(
        self,
        session_id: str,
        user_utterance: str,
        existing_cart: Optional[List[Dict[str, Any]]] = None
    ) -> TurnResponse:
        """
        Executes a single conversational turn:
        1. Normalizes input and identifies intra-utterance corrections.
        2. Detects user intent.
        3. Parses items, quantities, and units.
        4. Validates catalogue packaging and stock availability.
        5. Updates cart and produces spoken conversational reply.
        """
        # Load or initialize cart
        cart = CartService(initial_items=existing_cart)

        # 1. Normalize
        normalized = self.normalizer.normalize(user_utterance)

        # 2. Classify Intent (with awareness of current confirmation state)
        ctx = self.session_contexts.setdefault(session_id, {})
        is_awaiting_conf = ctx.get("awaiting_confirmation", False)
        intent, target_text = IntentClassifier.classify_intent(
            normalized.clean_text,
            has_intra_correction=normalized.has_correction,
            is_awaiting_confirmation=is_awaiting_conf
        )

        # 3. Handle Special Non-Add Intents First
        # -------------------------------------------------------------
        # Intent: CONFIRM
        # -------------------------------------------------------------
        if intent == IntentType.CONFIRM:
            total = cart.calculate_total()
            items = cart.get_items()
            if target_text == "request_bill":
                if not items:
                    msg = "Aapki cart abhi khali hai. Kuch samaan add kijiye."
                    action = TurnAction(
                        action="awaiting_confirmation",
                        items=[],
                        message=msg
                    )
                    ctx["awaiting_confirmation"] = False
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.COLLECTING,
                        action=action,
                        cart=[],
                        total_amount=Decimal(0),
                        spoken_response=msg
                    )
                else:
                    item_count = len(items)
                    msg = f"Aapka bill {item_count} items ke liye ₹{total} hua. Kya order confirm kar dein?"
                    action = TurnAction(
                        action="awaiting_confirmation",
                        items=items,
                        message=msg
                    )
                    ctx["awaiting_confirmation"] = True
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.AWAITING_CONFIRMATION,
                        action=action,
                        cart=items,
                        total_amount=total,
                        spoken_response=msg
                    )

            # Explicit confirmation (e.g. "Haan confirm kar do", "theek hai bhej do") -> ORDER_PLACED
            ctx["awaiting_confirmation"] = False
            if not items:
                msg = "Aapki cart abhi khali hai. Order confirm karne ke liye pehle kuch samaan add kijiye."
                action = TurnAction(
                    action="cart_empty",
                    items=[],
                    message=msg
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.COLLECTING,
                    action=action,
                    cart=[],
                    total_amount=Decimal(0),
                    spoken_response=msg
                )

            action = TurnAction(
                action="confirm_existing_cart",
                items=items,
                message=f"Aapka order confirm ho gaya hai. Total amount: ₹{total}."
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.ORDER_PLACED,
                action=action,
                cart=items,
                total_amount=total,
                spoken_response=action.message
            )

        # -------------------------------------------------------------
        # Intent: CANCEL / CLEAR CART
        # -------------------------------------------------------------
        if intent == IntentType.CANCEL:
            cart.clear()
            self.session_contexts.pop(session_id, None)
            is_cart_clear = any(w in normalized.clean_text.lower() for w in ["khali", "clear", "empty", "saaf", "sab", "saara", "reset"])
            if is_cart_clear:
                msg = "Ji bhaiya, aapki cart poori khali kar di hai. Aur kya chahiye bhaiya?"
                state = DialogueState.COLLECTING
            else:
                msg = "Aapka order cancel kar diya gaya hai."
                state = DialogueState.CANCELLED

            action = TurnAction(
                action="cancel_order",
                items=[],
                message=msg
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=state,
                action=action,
                cart=[],
                total_amount=Decimal(0),
                spoken_response=msg
            )

        # -------------------------------------------------------------
        # ReacTOD Programmatic Short-Circuit: GREETING & CHITCHAT
        # Bypasses downstream Slot Resolution and RAG entirely
        # -------------------------------------------------------------
        if intent == IntentType.GREETING:
            msg = "Namaste bhaiya! Everyday Needs General Store mein aapka swagat hai. Aaj aapko kya-kya chahiye?"
            action = TurnAction(
                action="greet",
                items=cart.get_items(),
                message=msg
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.COLLECTING,
                action=action,
                cart=cart.get_items(),
                total_amount=cart.calculate_total(),
                spoken_response=msg
            )

        if intent == IntentType.CHITCHAT:
            clean_t = normalized.clean_text.lower()
            if any(w in clean_t for w in ["kaise ho", "kya haal", "theek ho", "how are you"]):
                msg = "Hum bilkul theek hain bhaiya! Aap suniye, aaj dukaan se kya-kya saman pack karwaana hai?"
            else:
                msg = "Main DukaanSaathi hoon! Everyday Needs General Store ka voice assistant. Aap bolkar grocery items order kar sakte hain."
            action = TurnAction(
                action="chitchat",
                items=cart.get_items(),
                message=msg
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.COLLECTING,
                action=action,
                cart=cart.get_items(),
                total_amount=cart.calculate_total(),
                spoken_response=msg
            )

        # -------------------------------------------------------------
        # Intent: VIEW CART / CART QUERY / TOTAL INQUIRY
        # -------------------------------------------------------------
        if intent in [IntentType.CART_QUERY, IntentType.VIEW_CART]:
            items = cart.get_items()
            total = cart.calculate_total()
            clean_t = normalized.clean_text.lower()
            is_total_query = any(w in clean_t for w in ["total", "paise", "rupaye", "kharcha", "bill kitna"])

            if not items:
                msg = "Bhaiya, abhi aapke cart mein kuch nahi pada hai, cart bilkul khali hai. Bataiye kya-kya samaan add karoon?"
            elif is_total_query:
                msg = f"Aapki cart ka total ₹{total} hua hai ({len(items)} items hain). Final bill banana ho to 'bill bana do' bol dijiye."
            else:
                item_strs = [f"{it.quantity} {it.unit} {it.name}" for it in items]
                items_summary = ", ".join(item_strs)
                msg = f"Aapki cart mein {len(items)} items hain: {items_summary}. Total ₹{total} hua hai. Aur kya jiske aage add karna hai bhaiya?"

            action = TurnAction(
                action="review_cart",
                items=items,
                message=msg
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.COLLECTING,
                action=action,
                cart=items,
                total_amount=total,
                spoken_response=msg
            )

        # -------------------------------------------------------------
        # Intent: STORE INFORMATION (Hours, Location, Delivery, Payment)
        # -------------------------------------------------------------
        if intent == IntentType.STORE_INFO:
            clean_t = normalized.clean_text.lower()
            if any(w in clean_t for w in ["timing", "time", "samay", "kab", "khulti", "band"]):
                msg = "Everyday Needs General Store subah 7:00 baje se raat 10:00 baje tak khula rehta hai."
            elif any(w in clean_t for w in ["kahan", "kidhar", "address", "pata", "location"]):
                msg = "Everyday Needs General Store, Shop No. 4, Main Market, Delhi Road par sthit hai."
            elif any(w in clean_t for w in ["delivery", "home delivery"]):
                msg = "Haan ji bhaiya, humare paas 30 minute ke andar free home delivery uplabdh hai. Aap apna samaan bataiye!"
            elif any(w in clean_t for w in ["payment", "upi", "gpay", "phonepe", "paytm", "qr", "cash", "online"]):
                msg = "Haan ji bhaiya, hum Cash, PhonePe, Google Pay, Paytm aur UPI sabhi methods accept karte hain."
            else:
                msg = "Main DukaanSaathi hoon! Everyday Needs General Store ka voice assistant. Aap bolkar koi bhi grocery item add karwa sakte hain, cart edit kar sakte hain, aur hisaab dekh sakte hain."

            action = TurnAction(
                action="store_info",
                items=cart.get_items(),
                message=msg
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.COLLECTING,
                action=action,
                cart=cart.get_items(),
                total_amount=cart.calculate_total(),
                spoken_response=msg
            )

        # -------------------------------------------------------------
        # Intent: REMOVE ITEM (e.g. "Maggi hata do")
        # -------------------------------------------------------------
        if intent == IntentType.REMOVE:
            clean = normalized.clean_text
            # Extract item name before "hata do", "remove", "nahi chahiye", or "mat daalna"
            m = re.search(r"^(.*?)(?:\s+hata\s+do|\s+nikal\s+do|\s+remove|\s+delete|\s+nahi\s+chahiye|\s+mat\s+daalna|\s+mat\s+do)", clean)
            item_phrase = m.group(1).strip() if m else (target_text or clean)

            match_res = self.matcher.match_product(item_phrase)
            target_pid = match_res.product.product_id if match_res.matched else None

            # Fallback to search cart items
            removed_item = None
            if not target_pid:
                for it in cart.get_items():
                    if item_phrase in it.name.lower():
                        target_pid = it.product_id
                        break

            if target_pid and cart.remove_item(target_pid):
                action = TurnAction(
                    action="remove_item",
                    items=[],
                    message=f"Product cart se hata diya gaya hai."
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.COLLECTING,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )
            else:
                action = TurnAction(
                    action="remove_item",
                    items=[],
                    message="Yeh product cart mein nahi mila."
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.COLLECTING,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )

        # -------------------------------------------------------------
        # Intent: REPLACE / CORRECTION (e.g. "5 nahi 4 chahiye", "ek packet kam kar do", "2 ki jagah 1 packet")
        # -------------------------------------------------------------
        if intent == IntentType.REPLACE_QUANTITY:
            # Check intra-utterance: pre has product or previous quantity, post has new quantity
            if normalized.has_correction:
                pre_text = (normalized.correction_pre or "").strip()
                post_text = (normalized.correction_post or "").strip()

                is_pure_num = bool(re.match(r"^(?:\d+(?:\.\d+)?|ek|do|teen|chaar|paanch|panch|chhe|saat|aath|nau|das|aadha|half|pao|one|two|three|four|five)\s*(?:packet|pkt|bottle|kilo|kg|jar|pouch|piece|can|pack)?$", pre_text.lower()))

                match_res = None if is_pure_num else self.matcher.match_product(pre_text)
                if match_res and match_res.matched:
                    prod = self.inventory_service.get_product_details(match_res.product.product_id)
                    qty_info = QuantityParser.parse_quantity_phrase(post_text)
                    sell_qty, sell_unit, err = QuantityParser.resolve_package_quantity(prod, qty_info)
                    if sell_qty:
                        cart.set_item_quantity(prod.product_id, sell_qty)
                        action_item = cart.items.get(prod.product_id) or cart.add_or_update_item(
                            product_id=prod.product_id,
                            name=prod.name,
                            quantity=sell_qty,
                            unit=sell_unit,
                            unit_price=prod.price_inr,
                            requested_quantity=qty_info.raw_amount,
                            requested_unit=qty_info.raw_unit
                        )
                        action_label = "replace_quantity" if "kar do" in normalized.clean_text else "add_items"
                        total = cart.calculate_total()
                        msg = f"Ji bhaiya, {prod.name} ki quantity update karke {sell_qty} {sell_unit} kar di hai. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"
                        action = TurnAction(
                            action=action_label,
                            items=[action_item],
                            message=msg
                        )
                        return TurnResponse(
                            session_id=session_id,
                            intent=intent,
                            state=DialogueState.COLLECTING,
                            action=action,
                            cart=cart.get_items(),
                            total_amount=total,
                            spoken_response=msg
                        )
                else:
                    # pre_text is a quantity like "5" in "5 nahi 4 kar do" or "5 nahi 4 chahiye"
                    items_in_cart = cart.get_items()
                    if items_in_cart:
                        qty_info = QuantityParser.parse_quantity_phrase(post_text)
                        target_item = items_in_cart[-1]
                        ctx = self.session_contexts.get(session_id, {})
                        if ctx.get("last_cart_product_id") and ctx["last_cart_product_id"] in cart.items:
                            target_item = cart.items[ctx["last_cart_product_id"]]
                        else:
                            pre_qty = QuantityParser.parse_quantity_phrase(pre_text).raw_amount
                            if pre_qty:
                                for it in items_in_cart:
                                    if it.quantity == pre_qty:
                                        target_item = it
                                        break

                        prod = self.inventory_service.get_product_details(target_item.product_id)
                        sell_qty, sell_unit, _ = QuantityParser.resolve_package_quantity(prod, qty_info)
                        sell_qty = sell_qty or qty_info.raw_amount or Decimal("1")
                        cart.set_item_quantity(target_item.product_id, sell_qty)
                        updated_item = cart.items[target_item.product_id]
                        total = cart.calculate_total()
                        if qty_info.raw_unit in ["kg", "kilo"] and target_item.unit == "packet":
                            msg = f"Theek hai bhaiya, {qty_info.raw_amount} {qty_info.raw_unit} ke hisaab se {target_item.name} ke {sell_qty} packet kar diye hain. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"
                        else:
                            msg = f"Theek hai bhaiya, {target_item.name} ki quantity badal kar {sell_qty} {target_item.unit} kar di hai. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"
                        action = TurnAction(
                            action="replace_quantity",
                            items=[updated_item],
                            message=msg
                        )
                        return TurnResponse(
                            session_id=session_id,
                            intent=intent,
                            state=DialogueState.COLLECTING,
                            action=action,
                            cart=cart.get_items(),
                            total_amount=total,
                            spoken_response=msg
                        )
            else:
                items_in_cart = cart.get_items()
                clean = normalized.clean_text.lower()

                # Check Relative Reduction (e.g. "ek packet kam kar do", "1 kam kar do", "ek hata do")
                is_reduction = any(w in clean for w in ["kam kar do", "kam karo", "kam kar", "ghata do", "ghatao", "nikal do", "hata do", "kam kijiye"])

                # Check "X nahi Y" or "X ki jagah Y"
                m_subst = re.search(r"(\d+(?:\.\d+)?|ek|do|teen|chaar|paanch|panch|aadha)\s*(?:kg|kilo|gram|gm|packet|pack|bottle|litre|l|jar|pouch)?\s*(?:nahi|ki\s+jagah|k\s+badle)\s*(\d+(?:\.\d+)?|ek|do|teen|chaar|paanch|panch|aadha|\w+)", clean)

                # 1. If there is a pending quoted or clarified product from the immediately preceding turn,
                # a bare quantity request (e.g. "दो bottle कर दीजिए", "2 packet kar do") is an ADDITION for that pending product!
                has_pending_context = (
                    session_id in self.session_contexts
                    and (
                        self.session_contexts[session_id].get("pending_product_id")
                        or self.session_contexts[session_id].get("active_product_id")
                        or self.session_contexts[session_id].get("pending_clarification_candidates")
                    )
                )

                if has_pending_context:
                    qty_info = QuantityParser.parse_quantity_phrase(clean)
                    if qty_info.raw_amount:
                        pending_pid = (
                            self.session_contexts[session_id].pop("pending_product_id", None)
                            or self.session_contexts[session_id].pop("active_product_id", None)
                        )
                        self.session_contexts[session_id].pop("awaiting_slot", None)
                        if not pending_pid:
                            cands = self.session_contexts[session_id].pop("pending_clarification_candidates", [])
                            pending_pid = cands[0] if cands else None
                        if pending_pid:
                            prod = self.inventory_service.get_product_details(pending_pid)
                            sell_qty, sell_unit, err = QuantityParser.resolve_package_quantity(prod, qty_info)
                            sell_qty = sell_qty or qty_info.raw_amount or Decimal("1")
                            sell_unit = sell_unit or prod.sale_unit
                            action_item = cart.add_or_update_item(
                                product_id=prod.product_id,
                                name=prod.name,
                                quantity=sell_qty,
                                unit=sell_unit,
                                unit_price=prod.price_inr,
                                requested_quantity=qty_info.raw_amount,
                                requested_unit=qty_info.raw_unit
                            )
                            total = cart.calculate_total()
                            msg = f"Ji bhaiya, {sell_qty} {sell_unit} {prod.name} add kar diye hain. Total ₹{total} hua. Aur kya chahiye bhaiya?"
                            action = TurnAction(
                                action="add_items",
                                items=[action_item],
                                message=msg
                            )
                            return TurnResponse(
                                session_id=session_id,
                                intent=IntentType.ADD,
                                state=DialogueState.COLLECTING,
                                action=action,
                                cart=cart.get_items(),
                                total_amount=total,
                                spoken_response=msg
                            )

                if is_reduction and items_in_cart:
                    qty_info = QuantityParser.parse_quantity_phrase(clean)
                    reduce_amt = qty_info.raw_amount or Decimal("1")

                    target_item = items_in_cart[-1]
                    for it in items_in_cart:
                        if it.name.lower() in clean or (it.unit and it.unit.lower() in clean):
                            target_item = it
                            break

                    new_qty = target_item.quantity - reduce_amt
                    if new_qty <= 0:
                        cart.remove_item(target_item.product_id)
                        total = cart.calculate_total()
                        msg = f"Ji bhaiya, {target_item.name} cart se hata diya hai. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"
                    else:
                        cart.set_item_quantity(target_item.product_id, new_qty)
                        total = cart.calculate_total()
                        msg = f"Ji bhaiya, {target_item.name} ki quantity kam karke {new_qty} {target_item.unit} kar di hai. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"

                    action = TurnAction(
                        action="replace_quantity",
                        items=cart.get_items(),
                        message=msg
                    )
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.COLLECTING,
                        action=action,
                        cart=cart.get_items(),
                        total_amount=total,
                        spoken_response=msg
                    )

                elif m_subst and items_in_cart:
                    old_token = m_subst.group(1)
                    post_subst = re.split(r"(?:nahi|ki\s+jagah|k\s+badle)", clean, maxsplit=1)[-1]
                    target_qty_info = QuantityParser.parse_quantity_phrase(post_subst)
                    new_qty = target_qty_info.raw_amount or Decimal("1")

                    target_item = None
                    # 1. First priority: Check if a specific cart product was explicitly named in the utterance
                    for it in items_in_cart:
                        clean_it_name = it.name.lower()
                        # Direct name words check (e.g. "salt", "namak", "sugar", "coffee", "tea", "atta")
                        if any(w in clean for w in clean_it_name.split() if len(w) >= 3):
                            target_item = it
                            break
                        if ("namak" in clean or "salt" in clean) and ("salt" in clean_it_name or "namak" in clean_it_name):
                            target_item = it
                            break
                        if ("chini" in clean or "sugar" in clean) and ("sugar" in clean_it_name or "chini" in clean_it_name):
                            target_item = it
                            break
                        if ("coffee" in clean or "nescafe" in clean) and ("coffee" in clean_it_name or "nescafe" in clean_it_name):
                            target_item = it
                            break

                    # 2. Second priority: Check if an item in cart matches the old quantity
                    if not target_item:
                        old_qty = QuantityParser.parse_quantity_phrase(old_token).raw_amount
                        if old_qty:
                            for it in items_in_cart:
                                if it.quantity == old_qty:
                                    target_item = it
                                    break

                    # 3. Third priority: session context or last cart item
                    if not target_item:
                        ctx = self.session_contexts.get(session_id, {})
                        if ctx.get("last_cart_product_id") and ctx["last_cart_product_id"] in cart.items:
                            target_item = cart.items[ctx["last_cart_product_id"]]
                        else:
                            target_item = items_in_cart[-1]

                    prod = self.inventory_service.get_product_details(target_item.product_id)
                    sell_qty, sell_unit, _ = QuantityParser.resolve_package_quantity(prod, target_qty_info)
                    sell_qty = sell_qty or new_qty
                    cart.set_item_quantity(target_item.product_id, sell_qty)
                    total = cart.calculate_total()
                    if target_qty_info.raw_unit in ["kg", "kilo"] and target_item.unit == "packet":
                        msg = f"Theek hai bhaiya, {target_qty_info.raw_amount} {target_qty_info.raw_unit} ke hisaab se {target_item.name} ke {sell_qty} packet kar diye hain. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"
                    else:
                        msg = f"Ji bhaiya, {target_item.name} ki quantity update karke {sell_qty} {target_item.unit} kar di hai. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"
                    action = TurnAction(
                        action="replace_quantity",
                        items=[cart.items[target_item.product_id]],
                        message=msg
                    )
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.COLLECTING,
                        action=action,
                        cart=cart.get_items(),
                        total_amount=total,
                        spoken_response=msg
                    )

                elif items_in_cart:
                    qty_info = QuantityParser.parse_quantity_phrase(clean)
                    if qty_info.raw_amount:
                        target_item = items_in_cart[-1]
                        # Check if a product was named in clean
                        for it in items_in_cart:
                            clean_it_name = it.name.lower()
                            if any(w in clean for w in clean_it_name.split() if len(w) >= 4):
                                target_item = it
                                break

                        prod = self.inventory_service.get_product_details(target_item.product_id)
                        sell_qty, sell_unit, err = QuantityParser.resolve_package_quantity(prod, qty_info)
                        sell_qty = sell_qty or qty_info.raw_amount
                        if sell_qty:
                            cart.set_item_quantity(target_item.product_id, sell_qty)
                            total = cart.calculate_total()
                            msg = f"Ji bhaiya, {target_item.name} ki quantity update karke {sell_qty} {target_item.unit} kar di hai. Naya total ₹{total} hua. Aur kya chahiye bhaiya?"
                            action = TurnAction(
                                action="replace_quantity",
                                items=[cart.items[target_item.product_id]],
                                message=msg
                            )
                            return TurnResponse(
                                session_id=session_id,
                                intent=intent,
                                state=DialogueState.COLLECTING,
                                action=action,
                                cart=cart.get_items(),
                                total_amount=total,
                                spoken_response=msg
                            )
                elif not items_in_cart and (
                    session_id in self.session_contexts
                    and (
                        self.session_contexts[session_id].get("pending_product_id")
                        or self.session_contexts[session_id].get("pending_clarification_candidates")
                    )
                ):
                    qty_info = QuantityParser.parse_quantity_phrase(clean)
                    if qty_info.raw_amount:
                        pending_pid = self.session_contexts[session_id].pop("pending_product_id", None)
                        if not pending_pid:
                            cands = self.session_contexts[session_id].pop("pending_clarification_candidates", [])
                            pending_pid = cands[0] if cands else None
                        if pending_pid:
                            prod = self.inventory_service.get_product_details(pending_pid)
                            sell_qty, sell_unit, err = QuantityParser.resolve_package_quantity(prod, qty_info)
                            sell_qty = sell_qty or Decimal("1")
                            sell_unit = sell_unit or prod.sale_unit
                            action_item = cart.add_or_update_item(
                                product_id=prod.product_id,
                                name=prod.name,
                                quantity=sell_qty,
                                unit=sell_unit,
                                unit_price=prod.price_inr,
                                requested_quantity=qty_info.raw_amount,
                                requested_unit=qty_info.raw_unit
                            )
                            total = cart.calculate_total()
                            msg = f"Ji bhaiya, {sell_qty} {sell_unit} {prod.name} add kar diye hain. Total ₹{total} hua. Aur kya chahiye bhaiya?"
                            action = TurnAction(
                                action="add_items",
                                items=[action_item],
                                message=msg
                            )
                            return TurnResponse(
                                session_id=session_id,
                                intent=IntentType.ADD,
                                state=DialogueState.COLLECTING,
                                action=action,
                                cart=cart.get_items(),
                                total_amount=total,
                                spoken_response=msg
                            )

        # -------------------------------------------------------------
        # Intent: PRICE QUERY (e.g. "Amul Taaza aadha litre kitne ka hai?")
        # -------------------------------------------------------------
        if intent == IntentType.PRICE_QUERY:
            clean_q = normalized.clean_text.lower()
            for filler in [
                "kitne ka hai", "kitne ki hai", "kitna rate hai", "price kya hai",
                "kya bhaav hai", "how much is", "how much for", "hai", "ka", "ki", "ke"
            ]:
                clean_q = re.sub(rf"\b{re.escape(filler)}\b", " ", clean_q)
            clean_q = re.sub(r"\s+", " ", clean_q).strip()

            match_res = self.matcher.match_product(clean_q)
            if not match_res.matched:
                match_res = self.matcher.match_product(normalized.clean_text)

            matched_candidate = None
            if match_res.matched:
                prod = match_res.product
                self.session_contexts.setdefault(session_id, {})["pending_product_id"] = prod.product_id
                qty_info = QuantityParser.parse_quantity_phrase(normalized.clean_text)
                dummy_prod = self.inventory_service.get_product_details(prod.product_id)
                sell_qty, sell_unit, _ = QuantityParser.resolve_package_quantity(dummy_prod, qty_info)
                sell_qty = sell_qty or Decimal("1")
                price = prod.price_inr * sell_qty
                action = TurnAction(
                    action="quote_price",
                    items=[CartItem(
                        product_id=prod.product_id,
                        name=prod.name,
                        quantity=sell_qty,
                        unit=sell_unit or prod.sale_unit,
                        unit_price=prod.price_inr,
                        subtotal=price,
                        requested_quantity=qty_info.raw_amount,
                        requested_unit=qty_info.raw_unit
                    )],
                    price_quote=price,
                    message=f"{prod.name} ka price ₹{price} hai."
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.COLLECTING,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )

        # -------------------------------------------------------------
        # Intent: STOCK QUERY (e.g. "sauce hogi sauce", "HF hai kya aapke paas", "Do you have chocolate?")
        # -------------------------------------------------------------
        if intent == IntentType.STOCK_QUERY:
            clean_q = clean_conversational_entity(normalized.clean_text).lower()

            # Multi-turn Context Check 1: Sachet / Pouch inquiry while discussing shampoo/hair care
            prev_topic = self.session_contexts.get(session_id, {}).get("active_topic", "").lower()
            if not prev_topic and session_id in self.session_contexts and self.session_contexts[session_id].get("pending_clarification_candidates"):
                cand_pids = self.session_contexts[session_id]["pending_clarification_candidates"]
                if cand_pids:
                    first_p = self.inventory_service.get_product_details(cand_pids[0])
                    if first_p:
                        prev_topic = first_p.name.lower()
            if any(w in normalized.clean_text.lower() for w in ["sachet", "pouch"]) and ("shampoo" in prev_topic or "hair" in prev_topic or "clinic" in prev_topic):
                sachet_prod = self.db.query(Product).filter(
                    Product.store_id == self.store_id,
                    Product.product_id == "PRD182"
                ).first()
                if sachet_prod:
                    self.session_contexts.setdefault(session_id, {})["pending_product_id"] = sachet_prod.product_id
                    msg = f"Haan ji bhaiya, shampoo mein Clinic Plus ka sachet pack available hai, ₹{sachet_prod.price_inr} mein 16 sachets ka pack hai. Pack kar doon?"
                    action = TurnAction(
                        action="quote_stock",
                        items=[CartItem(
                            product_id=sachet_prod.product_id,
                            name=sachet_prod.name,
                            quantity=Decimal(1),
                            unit=sachet_prod.sale_unit,
                            unit_price=sachet_prod.price_inr,
                            subtotal=sachet_prod.price_inr
                        )],
                        stock_quote=Decimal(100),
                        price_quote=sachet_prod.price_inr,
                        message=msg
                    )
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.COLLECTING,
                        action=action,
                        cart=cart.get_items(),
                        total_amount=cart.calculate_total(),
                        spoken_response=msg
                    )

            # Multi-turn Context Check 2: Brand inquiry under active category (e.g. "TRESemme nahi hai kya?")
            if prev_topic and any(w in normalized.clean_text.lower() for w in ["nahi hai", "nahi milega", "nahi hoga", "nahi rakhte", "nhi hai", "nahi"]):
                avail_brands = []
                if "shampoo" in prev_topic:
                    avail_brands = ["Clinic Plus", "Head & Shoulders", "Sunsilk"]
                elif "sauce" in prev_topic or "ketchup" in prev_topic:
                    avail_brands = ["Kissan", "Maggi Pichkoo", "Ching's"]
                elif "noodles" in prev_topic or "maggi" in prev_topic:
                    avail_brands = ["Maggi", "Ching's Hakka Noodles", "Yippee"]
                elif "toothpaste" in prev_topic or "manjan" in prev_topic:
                    avail_brands = ["Colgate", "Sensodyne", "Dabur Red", "Close Up"]
                elif "soap" in prev_topic or "sabun" in prev_topic:
                    avail_brands = ["Lifebuoy", "Dettol", "Dove"]
                elif "oil" in prev_topic or "tel" in prev_topic:
                    avail_brands = ["Fortune", "Dhara", "Saffola", "Parachute"]
                elif "tea" in prev_topic or "chai" in prev_topic:
                    avail_brands = ["Tata Tea", "Red Label", "Taj Mahal"]
                elif "cold drink" in prev_topic or "peene" in prev_topic:
                    avail_brands = ["Coca-Cola", "Sprite", "Thums Up", "Limca"]
                elif "chocolate" in prev_topic or "toffee" in prev_topic:
                    avail_brands = ["Cadbury Dairy Milk", "KitKat", "5 Star"]
                elif any(c in prev_topic for c in ["cereal", "cornflakes", "chocos", "oats"]):
                    avail_brands = ["Kellogg's", "Quaker Oats"]
                else:
                    matched_cat_prods = self.db.query(Product.brand).filter(
                        Product.store_id == self.store_id,
                        Product.is_active == True,
                        Product.name.ilike(f"%{prev_topic}%")
                    ).distinct().all()
                    avail_brands = [b[0] for b in matched_cat_prods if b[0] and b[0].lower() != "local"][:4]

                topic_label = (
                    "shampoo" if "shampoo" in prev_topic
                    else "sauce" if any(w in prev_topic for w in ["sauce", "ketchup"])
                    else "noodles" if any(w in prev_topic for w in ["noodles", "maggi"])
                    else "toothpaste" if any(w in prev_topic for w in ["toothpaste", "manjan"])
                    else "soap" if any(w in prev_topic for w in ["soap", "sabun"])
                    else "oil" if any(w in prev_topic for w in ["oil", "tel"])
                    else "tea" if any(w in prev_topic for w in ["tea", "chai"])
                    else "cold drink" if any(w in prev_topic for w in ["cold drink", "peene"])
                    else "chocolate" if any(w in prev_topic for w in ["chocolate", "toffee"])
                    else "cereal" if any(w in prev_topic for w in ["cereal", "cornflakes", "chocos", "oats"])
                    else prev_topic
                )
                brand_asked = clean_q.title() if clean_q else "Yeh brand"
                if avail_brands:
                    brands_str = ", ".join(avail_brands[:-1]) + f" aur {avail_brands[-1]}" if len(avail_brands) > 1 else avail_brands[0]
                    msg = f"Nahi bhaiya, {brand_asked} abhi dukaan mein uplabdh nahi hai. Humaare paas {brands_str} {topic_label} hi uplabdh hain."
                    action = TurnAction(
                        action="product_not_found",
                        clarification_type=ClarificationType.PRODUCT_NOT_FOUND,
                        message=msg
                    )
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.COLLECTING,
                        action=action,
                        cart=cart.get_items(),
                        total_amount=cart.calculate_total(),
                        spoken_response=msg
                    )

            # Match product using clean entity
            match_res = self.matcher.match_product(clean_q)
            if not match_res.matched and not match_res.is_ambiguous:
                match_res = self.matcher.match_product(normalized.clean_text)

            matched_candidate = None
            if match_res.matched:
                prod = match_res.product
                ctx = self.session_contexts.setdefault(session_id, {})
                ctx["pending_product_id"] = prod.product_id
                ctx["active_product_id"] = prod.product_id
                ctx["awaiting_slot"] = "quantity"
                ctx["active_topic"] = prod.name.lower()
                avail, stock, _ = self.inventory_service.check_availability(prod.product_id, Decimal(0))
                if stock <= 0:
                    msg = f"Maaf kijiye bhaiya, '{prod.name}' abhi out of stock hai."
                else:
                    # Check if multi-option beverage/category inquiry (e.g. cold drink -> Coke + Sprite)
                    cat_prods = self.db.query(Product).filter(
                        Product.store_id == self.store_id,
                        Product.category == prod.category,
                        Product.is_active == True
                    ).all()
                    if any(w in clean_q for w in ["cold drink", "cold drinks", "peene"]):
                        cd_prods = [
                            p for p in cat_prods
                            if any(d in p.name.lower() for d in ["coca-cola", "sprite", "thums", "limca", "maaza"])
                        ]
                        prods_to_quote = cd_prods[:2] if len(cd_prods) >= 2 else cat_prods[:2]
                        self.session_contexts[session_id]["pending_product_ids"] = [p.product_id for p in prods_to_quote]
                        names_str = " aur ".join(p.name for p in prods_to_quote)
                        msg = f"Haan ji, humare pas {names_str} hain, ₹{prod.price_inr} per bottle. Kitna chahiye?"
                    else:
                        msg = f"Haan ji, {prod.name} uplabdh hai, ₹{prod.price_inr} प्रति {prod.sale_unit} hai. Aapko kitna chahiye?"

                action = TurnAction(
                    action="quote_stock",
                    items=[CartItem(
                        product_id=prod.product_id,
                        name=prod.name,
                        quantity=stock,
                        unit=prod.sale_unit,
                        unit_price=prod.price_inr,
                        subtotal=Decimal(0)
                    )],
                    stock_quote=stock,
                    price_quote=prod.price_inr,
                    message=msg
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.COLLECTING,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=msg
                )

            elif match_res.is_ambiguous:
                ctx = self.session_contexts.setdefault(session_id, {})
                ctx["pending_clarification_candidates"] = [
                    c.product_id for c in match_res.candidates
                ]
                ctx["active_candidates"] = ctx["pending_clarification_candidates"]
                ctx["awaiting_slot"] = "variant"
                ctx["active_topic"] = clean_q
                options_str = " ya ".join(match_res.clarification_options[:4])
                clarify_msg = f"Kaunsa chahiye: {options_str}?"
                action = TurnAction(
                    action=match_res.clarification_type.value if match_res.clarification_type else "clarify_product",
                    clarification_type=match_res.clarification_type,
                    clarification_options=match_res.clarification_options,
                    message=clarify_msg
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.NEEDS_CLARIFICATION,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=clarify_msg
                )

            else:
                display_query = clean_q.title() if clean_q else "Yeh item"
                if prev_topic:
                    avail_brands = []
                    if "shampoo" in prev_topic:
                        avail_brands = ["Clinic Plus", "Head & Shoulders", "Sunsilk"]
                    elif "sauce" in prev_topic or "ketchup" in prev_topic:
                        avail_brands = ["Kissan", "Maggi Pichkoo", "Ching's"]
                    elif "noodles" in prev_topic or "maggi" in prev_topic:
                        avail_brands = ["Maggi", "Ching's Hakka Noodles", "Yippee"]
                    elif "toothpaste" in prev_topic or "manjan" in prev_topic:
                        avail_brands = ["Colgate", "Sensodyne", "Dabur Red", "Close Up"]
                    elif "soap" in prev_topic or "sabun" in prev_topic:
                        avail_brands = ["Lifebuoy", "Dettol", "Dove"]
                    elif "oil" in prev_topic or "tel" in prev_topic:
                        avail_brands = ["Fortune", "Dhara", "Saffola", "Parachute"]
                    elif "tea" in prev_topic or "chai" in prev_topic:
                        avail_brands = ["Tata Tea", "Red Label", "Taj Mahal"]
                    elif "cold drink" in prev_topic or "peene" in prev_topic:
                        avail_brands = ["Coca-Cola", "Sprite", "Thums Up", "Limca"]
                    elif "chocolate" in prev_topic or "toffee" in prev_topic:
                        avail_brands = ["Cadbury Dairy Milk", "KitKat", "5 Star"]
                    elif any(c in prev_topic for c in ["cereal", "cornflakes", "chocos", "oats"]):
                        avail_brands = ["Kellogg's", "Quaker Oats"]

                    topic_label = (
                        "shampoo" if "shampoo" in prev_topic
                        else "sauce" if any(w in prev_topic for w in ["sauce", "ketchup"])
                        else "noodles" if any(w in prev_topic for w in ["noodles", "maggi"])
                        else "toothpaste" if any(w in prev_topic for w in ["toothpaste", "manjan"])
                        else "soap" if any(w in prev_topic for w in ["soap", "sabun"])
                        else "oil" if any(w in prev_topic for w in ["oil", "tel"])
                        else "tea" if any(w in prev_topic for w in ["tea", "chai"])
                        else "cold drink" if any(w in prev_topic for w in ["cold drink", "peene"])
                        else "chocolate" if any(w in prev_topic for w in ["chocolate", "toffee"])
                        else "cereal" if any(w in prev_topic for w in ["cereal", "cornflakes", "chocos", "oats"])
                        else prev_topic
                    )
                    if avail_brands:
                        brands_str = ", ".join(avail_brands[:-1]) + f" aur {avail_brands[-1]}" if len(avail_brands) > 1 else avail_brands[0]
                        msg = f"Nahi bhaiya, {display_query} abhi dukaan mein uplabdh nahi hai. Humaare paas {brands_str} {topic_label} hi uplabdh hain."
                    else:
                        if len(clean_q.split()) > 3 or any(w in clean_q for w in ["check", "tumhare", "paas", "kuch", "pada", "batao", "batana", "gaya"]):
                            msg = "Maaf kijiye bhaiya, main samajh nahi paya. Aapko dukaan se kya samaan chahiye?"
                        else:
                            msg = f"Maaf kijiye, '{display_query}' humaare store mein uplabdh nahi hai. Aur koi samaan chahiye?"
                else:
                    if len(clean_q.split()) > 3 or any(w in clean_q for w in ["check", "tumhare", "paas", "kuch", "pada", "batao", "batana", "gaya"]):
                        msg = "Maaf kijiye bhaiya, main samajh nahi paya. Aapko dukaan se kya samaan chahiye?"
                    else:
                        msg = f"Maaf kijiye, '{display_query}' humaare store mein uplabdh nahi hai. Aur koi samaan chahiye?"
                action = TurnAction(
                    action="product_not_found",
                    clarification_type=ClarificationType.PRODUCT_NOT_FOUND,
                    message=msg
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.COLLECTING,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=msg
                )

        # -------------------------------------------------------------
        # Intent: CATALOG / INVENTORY QUERY (e.g. "What items are there in your shop?", "aapke paas kya kya saman hai?")
        # -------------------------------------------------------------
        if intent == IntentType.CATALOG_QUERY:
            action = TurnAction(
                action="quote_catalog",
                message="Hamari dukaan mein sabhi daily grocery items uplabdh hain. Poori inventory table screen par bhej di hai."
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.COLLECTING,
                action=action,
                cart=cart.get_items(),
                total_amount=cart.calculate_total(),
                spoken_response=action.message
            )

        # -------------------------------------------------------------
        # Intent: ADD ITEMS (Default Ordering Flow)
        # Supports single-item and multi-item split ("aur", "and", ",")
        # -------------------------------------------------------------
        clean_text = normalized.clean_text

        # Strip conversational agreement/acknowledgement prefixes (e.g. "Theek hai,", "Acha,", "Haan,")
        clean_text = re.sub(r"^(theek hai|acha|haan|ok|ji)\s*[,]?\s*", "", clean_text, flags=re.IGNORECASE).strip()

        # Negation single utterance: e.g. TC022: "Do packet Maggi nahi, ek hi packet"
        if "nahi" in clean_text and not normalized.has_correction:
            parts = clean_text.split("nahi")
            if len(parts) == 2 and parts[1].strip():
                correction_text = parts[1].strip()
                if "ek hi" in correction_text:
                    correction_text = correction_text.replace("ek hi", "ek")
                # prepend the product from pre
                pre_prod_match = self.matcher.match_product(parts[0])
                if pre_prod_match.matched:
                    clean_text = f"{correction_text} {pre_prod_match.product.name}"
                else:
                    clean_text = correction_text

        # Protect known multi-word brand phrases containing 'and' or '&' from clause splitting
        clean_text = re.sub(r"\bhead\s+(?:and|&)\s+shoulders\b", "head_and_shoulders", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\bjohnson\s+(?:and|&)\s+johnson\b", "johnson_and_johnson", clean_text, flags=re.IGNORECASE)

        # Rejoin comma if followed by numbers, units, quantity words, continuation pronouns, personal pronouns, or action verbs (avoid splitting single request)
        clean_text = re.sub(
            r",\s*(\d+|ek|do|teen|chaar|paanch|chhe|saat|aath|nau|das|one|two|three|four|five|six|seven|eight|nine|ten|aadha|half|pao|pav|dedh|dhai|sau|kilo|kg|gm|gram|g|ml|l|litre|liter|packet|bottle|pack|pouch|box|piece|jar|mujhe|humko|mere|meri|uske|uska|to|cart|kar|de|daal|pack|add)\b",
            r" \1",
            clean_text,
            flags=re.IGNORECASE
        )

        # Split multi-item clauses: "aur", "and", comma
        raw_clauses = re.split(r"\s+aur\s+|\s+and\s+|,\s*", clean_text)
        raw_clauses = [
            c.replace("head_and_shoulders", "head and shoulders")
             .replace("johnson_and_johnson", "johnson and johnson")
             .strip()
            for c in raw_clauses if c.strip()
        ]
        clauses = [
            c for c in raw_clauses
            if c.lower() not in ["theek hai", "acha", "haan", "ok", "ji", "bhaiya", "please"]
        ] or raw_clauses

        added_items = []
        action_name = "add_items"

        # Check multi-product pending context first (e.g. "dono ki ek ek bottle kar do")
        if any(w in clean_text for w in ["dono", "donon", "both"]) and session_id in self.session_contexts and self.session_contexts[session_id].get("pending_product_ids"):
            pending_pids = self.session_contexts[session_id].pop("pending_product_ids", [])
            self.session_contexts[session_id].pop("pending_product_id", None)
            qty_info = QuantityParser.parse_quantity_phrase(clean_text)
            multi_items = []
            for pid in pending_pids:
                p_prod = self.inventory_service.get_product_details(pid)
                s_qty, s_unit, _ = QuantityParser.resolve_package_quantity(p_prod, qty_info)
                s_qty = s_qty or Decimal("1")
                s_unit = s_unit or p_prod.sale_unit
                added_it = cart.add_or_update_item(
                    product_id=p_prod.product_id,
                    name=p_prod.name,
                    quantity=s_qty,
                    unit=s_unit,
                    unit_price=p_prod.price_inr,
                    requested_quantity=qty_info.raw_amount,
                    requested_unit=qty_info.raw_unit
                )
                multi_items.append(added_it)
            names_str = " aur ".join(it.name for it in multi_items)
            total = cart.calculate_total()
            msg = f"Ji bhaiya, {names_str} add kar diye hain. Total ₹{total} hua. Aur kya chahiye bhaiya?"
            action = TurnAction(
                action="add_items",
                items=multi_items,
                message=msg
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.COLLECTING,
                action=action,
                cart=cart.get_items(),
                total_amount=total,
                spoken_response=msg
            )

        for clause in clauses:
            # Check unmeasurable quantity (TC021: "Thoda sa aata de dena")
            qty_info = QuantityParser.parse_quantity_phrase(clause)
            if qty_info.is_unmeasurable:
                action = TurnAction(
                    action="clarify_quantity",
                    items=[],
                    clarification_type=ClarificationType.QUANTITY,
                    message="Kripya batayein kitna quantity chahiye (jaise ek kilo ya aadha kilo)?"
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.NEEDS_CLARIFICATION,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )

            # Clean product query by stripping extracted quantity tokens and conversational filler words
            clean_clause_entity = clean_conversational_entity(clause)
            product_query = clean_clause_entity.lower()
            for filler in [
                "bhaiya", "please", "add kar do", "add karo", "kar do", "de do",
                "de dena", "dena", "chahiye", "add", "mujhe", "humko", "wala",
                "wali", "ke", "ka", "ki", "aur"
            ]:
                product_query = re.sub(rf"\b{re.escape(filler)}\b", " ", product_query)

            for qty_word in [
                "aadha", "half", "pao", "pav", "dedh", "dhai", "sau", "kilo", "kilos",
                "kg", "gram", "grams", "litre", "litres", "liter", "l", "ml", "packet",
                "packets", "pkt", "pouch", "pouches", "bottle", "bottles", "jar", "jars",
                "das", "nau", "aath", "saat", "chhe", "paanch", "chaar", "teen", "do", "ek",
                "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"
            ]:
                product_query = re.sub(rf"(?<!-)\b{re.escape(qty_word)}\b", " ", product_query)

            product_query = re.sub(r"\b\d+(?:\.\d+)?\b", " ", product_query)
            product_query = re.sub(r"\s+", " ", product_query).strip()

            if not product_query:
                product_query = clean_clause_entity or clause

            # 1. First priority: Check direct product match in catalogue using the whole clause or entity
            # If the user explicitly named a catalogue item (e.g. "Kissan Fresh Tomato Ketchup 1 kg" or "Amul Gold 500ml"),
            # it must resolve immediately rather than taking an arbitrary guess from pending context!
            match_res = self.matcher.match_product(clean_clause_entity)
            if not match_res.matched and not match_res.is_ambiguous:
                match_res = self.matcher.match_product(product_query)
            if not match_res.matched and not match_res.is_ambiguous:
                match_res = self.matcher.match_product(clause)

            matched_candidate = None
            if match_res.matched:
                matched_candidate = match_res.product
                if session_id in self.session_contexts:
                    self.session_contexts[session_id].pop("pending_clarification_candidates", None)
                    self.session_contexts[session_id].pop("pending_product_id", None)
                    self.session_contexts[session_id].pop("active_product_id", None)
                    self.session_contexts[session_id].pop("awaiting_slot", None)
            else:
                # 2. Check if referring to previously quoted/available item or answering quantity for pending product
                is_available_ref = any(w in clause.lower() for w in ["available", "jo packet", "wahi", "uske", "uska"])
                if session_id in self.session_contexts and (self.session_contexts[session_id].get("pending_product_id") or self.session_contexts[session_id].get("active_product_id")):
                    pending_pid = self.session_contexts[session_id].get("pending_product_id") or self.session_contexts[session_id].get("active_product_id")
                    pending_prod = self.inventory_service.get_product_details(pending_pid)
                    if pending_prod and (is_available_ref or is_turn_for_pending_product(clause, pending_prod, qty_info)):
                        matched_candidate = self.matcher._build_candidate(pending_pid, 1.0, clause, "session_context")
                        self.session_contexts[session_id].pop("pending_product_id", None)
                        self.session_contexts[session_id].pop("active_product_id", None)
                        self.session_contexts[session_id].pop("awaiting_slot", None)

                # 3. Check if user is answering a pending clarification choice from previous turn
                if not matched_candidate and session_id in self.session_contexts and self.session_contexts[session_id].get("pending_clarification_candidates"):
                    pending_cands = self.session_contexts[session_id]["pending_clarification_candidates"]
                    clause_lower = clause.lower()
                    chosen_pid = None

                    # A. Pure numeric or ordinal choice: "1", "pehla", "2", "doosra"
                    words_in_clause = clause_lower.split()
                    is_pure_ordinal = len(words_in_clause) <= 2 and any(w in ["1", "ek", "pehla", "pehle", "2", "do", "doosra", "dusra", "first", "second"] for w in words_in_clause)

                    if is_pure_ordinal:
                        if any(w in words_in_clause for w in ["1", "ek", "pehla", "pehle", "first"]) and len(pending_cands) >= 1:
                            chosen_pid = pending_cands[0]
                        elif any(w in words_in_clause for w in ["2", "do", "doosra", "dusra", "second"]) and len(pending_cands) >= 2:
                            chosen_pid = pending_cands[1]
                    else:
                        # B. Score each candidate by brand, name tokens, and pack size
                        best_score = 0
                        for c_pid in pending_cands:
                            p = self.inventory_service.get_product_details(c_pid)
                            if not p:
                                continue
                            n_lower = p.name.lower()
                            score = 0
                            b_lower = (p.brand or "").lower()
                            if b_lower and b_lower != "local" and b_lower in clause_lower:
                                score += 50
                            cand_name_clean = re.sub(r"\s+\d+.*$", "", n_lower).strip()
                            if cand_name_clean and cand_name_clean in clause_lower:
                                score += 40
                            # Pack size check
                            m_size = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|litre|liter|g|gm|kg|kilo)\b", n_lower)
                            if m_size:
                                size_num = m_size.group(1)
                                size_unit = m_size.group(2)
                                if re.search(rf"\b{size_num}\s*(?:{size_unit})?\b", clause_lower):
                                    score += 30
                            if score > best_score and score >= 40:
                                best_score = score
                                chosen_pid = c_pid

                    if chosen_pid:
                        self.session_contexts[session_id].pop("pending_clarification_candidates", None)
                        matched_candidate = self.matcher._build_candidate(chosen_pid, 1.0, clause, "clarification_choice")

            if not matched_candidate:
                if (
                    not match_res.is_ambiguous
                    and session_id in self.session_contexts
                    and self.session_contexts[session_id].get("pending_product_id")
                    and (qty_info.raw_amount is not None or qty_info.rupee_amount is not None or any(w in clause.lower() for w in ["haan", "theek", "ok", "de do", "dena", "daal do", "yes"]))
                ):
                    pending_pid = self.session_contexts[session_id].pop("pending_product_id")
                    matched_candidate = self.matcher._build_candidate(pending_pid, 1.0, clause, "session_context")
                elif match_res.is_ambiguous:
                    self.session_contexts.setdefault(session_id, {})["pending_clarification_candidates"] = [
                        c.product_id for c in match_res.candidates
                    ]
                    self.session_contexts[session_id]["active_topic"] = product_query or clean_clause_entity
                    options_str = " ya ".join(match_res.clarification_options[:4])
                    clarify_msg = f"Kaunsa chahiye: {options_str}?"
                    action = TurnAction(
                        action=match_res.clarification_type.value if match_res.clarification_type else "clarify_product",
                        clarification_type=match_res.clarification_type,
                        clarification_options=match_res.clarification_options,
                        message=clarify_msg
                    )
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.NEEDS_CLARIFICATION,
                        action=action,
                        cart=cart.get_items(),
                        total_amount=cart.calculate_total(),
                        spoken_response=action.message
                    )

            if not matched_candidate:
                # Product not found in catalogue (TC026: "dragon fruit")
                # Check multi-product pending context (e.g. "dono ki ek ek bottle kar do")
                if any(w in clean_text for w in ["dono", "donon", "both"]) and session_id in self.session_contexts and self.session_contexts[session_id].get("pending_product_ids"):
                    pending_pids = self.session_contexts[session_id].pop("pending_product_ids")
                    multi_items = []
                    for pid in pending_pids:
                        p_prod = self.inventory_service.get_product_details(pid)
                        s_qty, s_unit, _ = QuantityParser.resolve_package_quantity(p_prod, qty_info)
                        s_qty = s_qty or Decimal("1")
                        s_unit = s_unit or p_prod.sale_unit
                        added_it = cart.add_or_update_item(
                            product_id=p_prod.product_id,
                            name=p_prod.name,
                            quantity=s_qty,
                            unit=s_unit,
                            unit_price=p_prod.price_inr,
                            requested_quantity=qty_info.raw_amount,
                            requested_unit=qty_info.raw_unit
                        )
                        multi_items.append(added_it)
                    names_str = " aur ".join(it.name for it in multi_items)
                    total = cart.calculate_total()
                    msg = f"Ji bhaiya, {names_str} add kar diye hain. Total ₹{total} hua. Aur kya chahiye bhaiya?"
                    action = TurnAction(
                        action="add_items",
                        items=multi_items,
                        message=msg
                    )
                    return TurnResponse(
                        session_id=session_id,
                        intent=intent,
                        state=DialogueState.COLLECTING,
                        action=action,
                        cart=cart.get_items(),
                        total_amount=total,
                        spoken_response=msg
                    )

                clean_disp = clean_conversational_entity(product_query or clause)
                display_query = clean_disp.title() if clean_disp else "Yeh item"

                active_top = self.session_contexts.get(session_id, {}).get("active_topic", "").lower()
                if not active_top and session_id in self.session_contexts and self.session_contexts[session_id].get("pending_clarification_candidates"):
                    c_pids = self.session_contexts[session_id]["pending_clarification_candidates"]
                    if c_pids:
                        f_p = self.inventory_service.get_product_details(c_pids[0])
                        if f_p:
                            active_top = f_p.name.lower()

                avail_brands = []
                if "shampoo" in active_top:
                    avail_brands = ["Clinic Plus", "Head & Shoulders", "Sunsilk"]
                elif "sauce" in active_top or "ketchup" in active_top:
                    avail_brands = ["Kissan", "Maggi Pichkoo", "Ching's"]
                elif "noodles" in active_top or "maggi" in active_top:
                    avail_brands = ["Maggi", "Ching's Hakka Noodles", "Yippee"]
                elif "toothpaste" in active_top or "manjan" in active_top:
                    avail_brands = ["Colgate", "Sensodyne", "Dabur Red", "Close Up"]
                elif "soap" in active_top or "sabun" in active_top:
                    avail_brands = ["Lifebuoy", "Dettol", "Dove"]
                elif "oil" in active_top or "tel" in active_top:
                    avail_brands = ["Fortune", "Dhara", "Saffola", "Parachute"]
                elif "tea" in active_top or "chai" in active_top:
                    avail_brands = ["Tata Tea", "Red Label", "Taj Mahal"]
                elif "cold drink" in active_top or "peene" in active_top:
                    avail_brands = ["Coca-Cola", "Sprite", "Thums Up", "Limca"]
                elif "chocolate" in active_top or "toffee" in active_top:
                    avail_brands = ["Cadbury Dairy Milk", "KitKat", "5 Star"]
                elif any(c in active_top for c in ["cereal", "cornflakes", "chocos", "oats"]):
                    avail_brands = ["Kellogg's", "Quaker Oats"]

                topic_label = (
                    "shampoo" if "shampoo" in active_top
                    else "sauce" if any(w in active_top for w in ["sauce", "ketchup"])
                    else "noodles" if any(w in active_top for w in ["noodles", "maggi"])
                    else "toothpaste" if any(w in active_top for w in ["toothpaste", "manjan"])
                    else "soap" if any(w in active_top for w in ["soap", "sabun"])
                    else "oil" if any(w in active_top for w in ["oil", "tel"])
                    else "tea" if any(w in active_top for w in ["tea", "chai"])
                    else "cold drink" if any(w in active_top for w in ["cold drink", "peene"])
                    else "chocolate" if any(w in active_top for w in ["chocolate", "toffee"])
                    else "cereal" if any(w in active_top for w in ["cereal", "cornflakes", "chocos", "oats"])
                    else active_top
                )

                if avail_brands and any(w in clause.lower() for w in ["nahi", "brand", "wala", "wali"]):
                    brands_str = ", ".join(avail_brands[:-1]) + f" aur {avail_brands[-1]}" if len(avail_brands) > 1 else avail_brands[0]
                    not_found_msg = f"Nahi bhaiya, {display_query} abhi dukaan mein uplabdh nahi hai. Humaare paas {brands_str} {topic_label} hi uplabdh hain."
                elif len(clean_disp.split()) > 3 or any(w in clean_disp.lower() for w in ["check", "tumhare", "paas", "kuch", "pada", "batao", "batana", "gaya"]):
                    not_found_msg = "Maaf kijiye bhaiya, main samajh nahi paya. Aapko dukaan se kya samaan chahiye?"
                else:
                    not_found_msg = f"Maaf kijiye, '{display_query}' humaare store mein uplabdh nahi hai. Aur koi samaan chahiye?"

                action = TurnAction(
                    action="product_not_found",
                    clarification_type=ClarificationType.PRODUCT_NOT_FOUND,
                    message=not_found_msg
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.NEEDS_CLARIFICATION,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )
            prod = self.inventory_service.get_product_details(matched_candidate.product_id)

            # Real Kirana missing-quantity check:
            # If user made an order request with imperative action verb ("kar do", "kar dijiye", "de do", "add kar do")
            # or is picking from clarification options on a discrete packaged item, default to 1 unit
            has_action_verb = any(v in clause.lower() for v in ["kar do", "kar dijiye", "de do", "de dijiye", "dena", "daal do", "daal dijiye", "add kar", "pack kar", "bhejo", "lao"])
            was_pending = session_id in self.session_contexts and self.session_contexts[session_id].get("pending_product_id") == prod.product_id
            is_from_choice = getattr(matched_candidate, "match_source", "") in ["clarification_choice", "session_context"]

            if not qty_info.is_explicit:
                if (has_action_verb or was_pending or is_from_choice) and prod.sale_unit.lower() in ["bottle", "packet", "pouch", "piece", "jar", "can", "box", "unit"]:
                    qty_info = ExtractedQuantity(
                        raw_amount=Decimal("1"),
                        raw_unit=prod.sale_unit,
                        normalized_amount=Decimal("1"),
                        normalized_unit=prod.sale_unit,
                        is_explicit=True
                    )

            # Bare inquiry check without quantity and without action verbs (e.g. "shampoo hai?", "chawal hai kya?"):
            if len(clauses) == 1 and not qty_info.is_explicit and not is_from_choice:
                ctx = self.session_contexts.setdefault(session_id, {})
                ctx["pending_product_id"] = prod.product_id
                ctx["active_product_id"] = prod.product_id
                ctx["awaiting_slot"] = "quantity"
                ctx["active_topic"] = prod.name.lower()
                
                # If matched category or multiple related options exist (e.g. cold drinks)
                cat_prods = self.db.query(Product).filter(
                    Product.store_id == self.store_id,
                    Product.category == prod.category,
                    Product.is_active == True
                ).all()
                if len(cat_prods) >= 2 and any(w in clause.lower() for w in ["cold drink", "tel", "biscuit", "soap", "sabun", "shampoo"]):
                    self.session_contexts[session_id]["pending_product_ids"] = [p.product_id for p in cat_prods[:2]]

                rate_str = f"₹{prod.price_inr} प्रति {prod.sale_unit}"
                ask_msg = f"Haan ji, {prod.name} uplabdh hai, {rate_str} hai. Aapko kitna chahiye?"
                action = TurnAction(
                    action="clarify_quantity",
                    clarification_type=ClarificationType.QUANTITY,
                    message=ask_msg
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.NEEDS_CLARIFICATION,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=ask_msg
                )

            # Reconcile quantity with package specifications
            sell_qty, sell_unit, pkg_err = QuantityParser.resolve_package_quantity(prod, qty_info)

            # Incompatible unit check (TC027: "Ek Maggi ka aadha kilo")
            if pkg_err == "clarify_unit":
                action = TurnAction(
                    action="clarify_unit",
                    clarification_type=ClarificationType.UNIT,
                    message=f"{prod.name} sirf {prod.sale_unit} mein uplabdh hai."
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.NEEDS_CLARIFICATION,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )

            # Sealed fixed package split fraction check (TC013: 250g besan when only 1kg packet exists)
            if pkg_err == "clarify_package_fraction":
                action = TurnAction(
                    action="clarify_or_reject",
                    clarification_type=ClarificationType.UNSUPPORTED_PACKAGE_FRACTION,
                    message=f"{prod.name} sirf {prod.pack_size} {prod.pack_size_unit} ke fixed pack mein uplabdh hai."
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.NEEDS_CLARIFICATION,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )

            sell_qty = sell_qty or Decimal("1")
            sell_unit = sell_unit or prod.sale_unit

            # Check inventory availability (TC015 boundary test, TC016 insufficient stock test)
            is_avail, current_stock, threshold = self.inventory_service.check_availability(prod.product_id, sell_qty)
            if not is_avail:
                ctx = self.session_contexts.setdefault(session_id, {})
                ctx["pending_product_id"] = prod.product_id
                ctx["active_product_id"] = prod.product_id
                ctx["awaiting_slot"] = "stock_confirmation"
                if current_stock <= 0:
                    msg = f"Maaf kijiye, '{prod.name}' abhi out of stock hai."
                else:
                    msg = f"'{prod.name}' ke abhi sirf {current_stock} {sell_unit} available hain. Kya {current_stock} add kar doon?"
                action = TurnAction(
                    action="reject_insufficient_stock",
                    clarification_type=ClarificationType.INSUFFICIENT_STOCK,
                    stock_quote=current_stock,
                    message=msg
                )
                return TurnResponse(
                    session_id=session_id,
                    intent=intent,
                    state=DialogueState.NEEDS_CLARIFICATION,
                    action=action,
                    cart=cart.get_items(),
                    total_amount=cart.calculate_total(),
                    spoken_response=action.message
                )

            # Special tag for check_stock test (TC014: stock is low but available)
            if current_stock <= threshold and action_name == "add_items":
                action_name = "check_stock"

            # Add item to cart
            cart_item = cart.add_or_update_item(
                product_id=prod.product_id,
                name=prod.name,
                quantity=sell_qty,
                unit=sell_unit,
                unit_price=prod.price_inr,
                requested_quantity=qty_info.raw_amount,
                requested_unit=qty_info.raw_unit
            )
            # Track last cart product id for follow-up corrections
            ctx = self.session_contexts.setdefault(session_id, {})
            ctx["last_cart_product_id"] = prod.product_id
            ctx["active_product_id"] = None
            ctx["pending_product_id"] = None
            ctx["awaiting_slot"] = None
            added_items.append(cart_item)

        # Deduplicate added_items by product_id preserving order (using latest cart state)
        seen_pids = set()
        unique_added_items = []
        for it in added_items:
            if it.product_id not in seen_pids:
                seen_pids.add(it.product_id)
                unique_added_items.append(it)
        added_items = unique_added_items

        total_amount = cart.calculate_total()
        # Intelligent phrasing for pack conversion (e.g. 1 kg -> 4 packet 250g)
        if len(added_items) == 1 and added_items[0].requested_unit in ["kg", "kilo"] and added_items[0].unit == "packet":
            req_str = f"{added_items[0].requested_quantity} {added_items[0].requested_unit}"
            spoken_reply = f"Ji bhaiya, {req_str} ke hisaab se {int(added_items[0].quantity)} packet {added_items[0].name} add kar diye hain. Total ₹{total_amount} hua. Aur kya chahiye bhaiya?"
        else:
            item_names = ", ".join([f"{it.quantity} {it.unit} {it.name}" for it in added_items])
            spoken_reply = f"Ji bhaiya, {item_names} add kar diye hain. Total ₹{total_amount} hua. Aur kya chahiye bhaiya?"

        action = TurnAction(
            action=action_name,
            items=added_items,
            message=spoken_reply
        )

        return TurnResponse(
            session_id=session_id,
            intent=intent,
            state=DialogueState.COLLECTING,
            action=action,
            cart=cart.get_items(),
            total_amount=total_amount,
            spoken_response=spoken_reply
        )
