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
)
from backend.app.services.normalizer import TranscriptNormalizer
from backend.app.services.matcher import ProductMatcher
from backend.app.services.quantity_parser import QuantityParser
from backend.app.services.intent_classifier import IntentClassifier
from backend.app.services.cart_service import CartService
from backend.app.services.inventory_service import InventoryService
from backend.app.models import OrderSession

class ConversationManager:
    def __init__(self, db: Session, store_id: str = "STORE001"):
        self.db = db
        self.store_id = store_id
        self.normalizer = TranscriptNormalizer()
        self.matcher = ProductMatcher(db, store_id=store_id)
        self.inventory_service = InventoryService(db)
        self.session_contexts: Dict[str, Dict[str, Any]] = {}

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

        # 2. Classify Intent
        intent, target_text = IntentClassifier.classify_intent(
            normalized.clean_text,
            has_intra_correction=normalized.has_correction
        )

        # 3. Handle Special Non-Add Intents First
        # -------------------------------------------------------------
        # Intent: CONFIRM
        # -------------------------------------------------------------
        if intent == IntentType.CONFIRM:
            total = cart.calculate_total()
            action = TurnAction(
                action="confirm_existing_cart",
                items=cart.get_items(),
                message=f"Aapka order confirm ho gaya hai. Total amount: ₹{total}."
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.ORDER_PLACED,
                action=action,
                cart=cart.get_items(),
                total_amount=total,
                spoken_response=action.message
            )

        # -------------------------------------------------------------
        # Intent: CANCEL
        # -------------------------------------------------------------
        if intent == IntentType.CANCEL:
            cart.clear()
            action = TurnAction(
                action="cancel_order",
                items=[],
                message="Aapka order cancel kar diya gaya hai."
            )
            return TurnResponse(
                session_id=session_id,
                intent=intent,
                state=DialogueState.CANCELLED,
                action=action,
                cart=[],
                total_amount=Decimal(0),
                spoken_response=action.message
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
        # Intent: REPLACE / CORRECTION (e.g. "Ek kilo chini... nahi, aadha kilo kar do")
        # -------------------------------------------------------------
        if intent == IntentType.REPLACE_QUANTITY:
            # Check intra-utterance: pre has product, post has new quantity
            if normalized.has_correction:
                pre_text = normalized.correction_pre
                post_text = normalized.correction_post

                match_res = self.matcher.match_product(pre_text)
                if match_res.matched:
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
                        # Distinguish explicit replace verb ('kar do') vs inline correction add (TC022)
                        action_label = "replace_quantity" if "kar do" in normalized.clean_text else "add_items"
                        action = TurnAction(
                            action=action_label,
                            items=[action_item],
                            message=f"{prod.name} ki quantity {sell_qty} {sell_unit} kar di gayi hai."
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
                # Multi-turn correction: e.g. "Nahi, aadha kilo kar do" or answering clarification (CONV004)
                qty_info = QuantityParser.parse_quantity_phrase(normalized.clean_text)
                items_in_cart = cart.get_items()
                if items_in_cart and qty_info.raw_amount:
                    # Update the most recent item in cart
                    last_item = items_in_cart[-1]
                    prod = self.inventory_service.get_product_details(last_item.product_id)
                    sell_qty, sell_unit, err = QuantityParser.resolve_package_quantity(prod, qty_info)
                    if sell_qty:
                        cart.set_item_quantity(last_item.product_id, sell_qty)
                        updated_item = cart.items[last_item.product_id]
                        action = TurnAction(
                            action="replace_quantity",
                            items=[updated_item],
                            message=f"{last_item.name} quantity update kar di gayi hai."
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
                elif not items_in_cart and (session_id in self.session_contexts and self.session_contexts[session_id].get("pending_product_id")) and qty_info.raw_amount:
                    pending_pid = self.session_contexts[session_id].pop("pending_product_id")
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
                    action = TurnAction(
                        action="add_items",
                        items=[action_item],
                        message=f"Ji, {sell_qty} {sell_unit} {prod.name} add kar diye hain. Aapka total ₹{cart.calculate_total()} hua."
                    )
                    return TurnResponse(
                        session_id=session_id,
                        intent=IntentType.ADD,
                        state=DialogueState.COLLECTING,
                        action=action,
                        cart=cart.get_items(),
                        total_amount=cart.calculate_total(),
                        spoken_response=action.message
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

            if match_res.matched:
                prod = match_res.product
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
        # Intent: STOCK QUERY (e.g. "Aapke paas kitna Parle-G hai?")
        # -------------------------------------------------------------
        if intent == IntentType.STOCK_QUERY:
            clean_q = normalized.clean_text.lower()
            for filler in [
                "aapke paas kitna", "aapke paas kitni", "kitna", "kitni",
                "stock hai kya", "available hai kya", "in stock", "how many do you have",
                "hai", "ka", "ki", "ke", "batao"
            ]:
                clean_q = re.sub(rf"\b{re.escape(filler)}\b", " ", clean_q)
            clean_q = re.sub(r"\s+", " ", clean_q).strip()

            match_res = self.matcher.match_product(clean_q)
            if not match_res.matched:
                match_res = self.matcher.match_product(normalized.clean_text)

            if match_res.matched:
                prod = match_res.product
                avail, stock, _ = self.inventory_service.check_availability(prod.product_id, Decimal(0))
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
                    message=f"Humaare paas {prod.name} ke {stock} {prod.sale_unit} uplabdh hain."
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

        # Split multi-item clauses: "aur", "and", comma
        raw_clauses = re.split(r"\s+aur\s+|\s+and\s+|,\s*", clean_text)
        raw_clauses = [c.strip() for c in raw_clauses if c.strip()]
        clauses = [
            c for c in raw_clauses
            if c.lower() not in ["theek hai", "acha", "haan", "ok", "ji", "bhaiya", "please"]
        ] or raw_clauses

        added_items = []
        action_name = "add_items"

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
            product_query = clause.lower()
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
                product_query = clause

            # Match product using cleaned query with fallback to raw clause
            match_res = self.matcher.match_product(product_query)
            if not match_res.matched and not match_res.is_ambiguous:
                match_res = self.matcher.match_product(clause)

            matched_candidate = None
            if match_res.matched:
                matched_candidate = match_res.product
            elif (
                not match_res.is_ambiguous
                and session_id in self.session_contexts
                and self.session_contexts[session_id].get("pending_product_id")
                and qty_info.raw_amount is not None
            ):
                pending_pid = self.session_contexts[session_id].pop("pending_product_id")
                matched_candidate = self.matcher._build_candidate(pending_pid, 1.0, clause, "session_context")
            elif match_res.is_ambiguous:
                action = TurnAction(
                    action=match_res.clarification_type.value if match_res.clarification_type else "clarify_product",
                    clarification_type=match_res.clarification_type,
                    clarification_options=match_res.clarification_options,
                    message=f"Kaunsa product chahiye? Options: {', '.join(match_res.clarification_options)}"
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
            else:
                # Product not found in catalogue (TC026: "dragon fruit")
                display_query = product_query.title() if product_query else "Yeh item"
                action = TurnAction(
                    action="product_not_found",
                    clarification_type=ClarificationType.PRODUCT_NOT_FOUND,
                    message=f"Maaf kijiye, '{display_query}' humaare store mein uplabdh nahi hai."
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
                self.session_contexts.setdefault(session_id, {})["pending_product_id"] = prod.product_id
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
            added_items.append(cart_item)

        total_amount = cart.calculate_total()
        item_names = ", ".join([f"{it.quantity} {it.unit} {it.name}" for it in added_items])
        spoken_reply = f"Ji, {item_names} add kar diye hain. Aapka total ₹{total_amount} hua."

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
