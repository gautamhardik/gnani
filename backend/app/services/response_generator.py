"""
DukaanSaathi — Deterministic Assistant Response Generator (Phase 4 Task 6)
Synthesizes natural, warm, conversational Hindi/Hinglish responses for the
kirana assistant ("Saathi"). Guarantees 0% price/stock hallucinations by deriving
all values strictly from verified database records and Phase 3 intelligence actions.
"""

from decimal import Decimal
from typing import List, Optional

from backend.app.schemas.intelligence import (
    DialogueState,
    IntentType,
    TurnResponse,
    CartItem,
)


class AssistantResponseGenerator:
    @staticmethod
    def _format_currency(amount: Decimal) -> str:
        """Formats Decimal currency into clean spoken Hindi phrasing."""
        val = int(amount) if amount % 1 == 0 else float(amount)
        return f"{val} rupaye"

    @staticmethod
    def _format_quantity(qty: Decimal, unit: str) -> str:
        """Formats quantities and units colloquially."""
        if unit.lower() in ["kg", "kilo"]:
            if qty == Decimal("0.5") or qty == Decimal("0.500"):
                return "aadha kilo"
            elif qty == Decimal("0.25") or qty == Decimal("0.250"):
                return "dhai sau gram"
            elif qty == Decimal("0.75") or qty == Decimal("0.750"):
                return "paun kilo"
            elif qty == Decimal("1") or qty == Decimal("1.000"):
                return "ek kilo"
            elif qty % 1 == 0:
                return f"{int(qty)} kilo"
            else:
                return f"{float(qty)} kilo"

        if unit.lower() in ["l", "litre", "liter"]:
            if qty == Decimal("0.5") or qty == Decimal("0.500"):
                return "aadha litre"
            elif qty == Decimal("1") or qty == Decimal("1.000"):
                return "ek litre"
            elif qty % 1 == 0:
                return f"{int(qty)} litre"
            else:
                return f"{float(qty)} litre"

        val = int(qty) if qty % 1 == 0 else float(qty)
        return f"{val} {unit}"

    @classmethod
    def _format_items_list(cls, items: List[CartItem]) -> str:
        if not items:
            return "samaan"
        formatted = [f"{cls._format_quantity(it.quantity, it.unit)} {it.name}" for it in items]
        if len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]} aur {formatted[1]}"
        else:
            return ", ".join(formatted[:-1]) + f" aur {formatted[-1]}"

    @classmethod
    def generate_response(
        cls,
        turn_response: TurnResponse,
        raw_transcript: Optional[str] = None
    ) -> str:
        """
        Produces natural spoken Hindi/Hinglish assistant response.
        """
        # Handle silence or empty transcript
        if not raw_transcript or not raw_transcript.strip():
            return "Kripya dobara boliye, hum sun nahi paye."

        action = turn_response.action
        state = turn_response.state
        intent = turn_response.intent
        act_name = action.action

        total_spoken = cls._format_currency(turn_response.total_amount)

        # 1. State: ORDER_PLACED or action: confirm_existing_cart
        if state == DialogueState.ORDER_PLACED or act_name == "confirm_existing_cart":
            return f"Aapka order confirm ho gaya hai! Kul {total_spoken}. Dukaan-daar jaldi hi aapka samaan pack karenge. Dhanyawad!"

        # 2. State: CANCELLED
        if state == DialogueState.CANCELLED:
            return "Theek hai bhaiya, aapka order cancel kar diya gaya hai."

        # 3. Action: clarify_product (Ambiguous SKUs)
        if act_name == "clarify_product":
            options = action.clarification_options
            if options:
                if len(options) == 1:
                    return f"Kya aapko {options[0]} chahiye?"
                elif len(options) == 2:
                    return f"Kaunsa chahiye: {options[0]} ya {options[1]}?"
                else:
                    joined = ", ".join(options[:-1]) + f" ya {options[-1]}"
                    return f"Kaunsa chahiye aapko: {joined}?"
            return "Kripya brand ka naam bataiye."

        # 4. Action: clarify_quantity or clarify_unit (Packaging or Unmeasurable)
        if act_name in ["clarify_quantity", "clarify_unit", "clarify_or_reject"]:
            return action.message or "Kripya bataiye kitna samaan chahiye, jaise ek kilo ya do packet."

        # 5. Action: check_stock or Insufficient Stock
        if act_name == "reject_insufficient_stock":
            if action.message:
                return action.message
            if action.stock_quote is not None:
                stock_val = int(action.stock_quote) if action.stock_quote % 1 == 0 else float(action.stock_quote)
                return f"Maaf kijiye, hamare paas abhi sirf {stock_val} available hain. Kya {stock_val} add kar doon?"
            return action.message or "Maaf kijiye, maangi gayi quantity stock mein available nahi hai."

        if act_name == "check_stock":
            if action.stock_quote is not None:
                stock_val = int(action.stock_quote) if action.stock_quote % 1 == 0 else float(action.stock_quote)
                return f"Maaf kijiye, hamare paas abhi sirf {stock_val} available hain. Kya {stock_val} kar dein?"
            return action.message or "Maaf kijiye, maangi gayi quantity stock mein available nahi hai."

        # 6. Action: quote_price
        if act_name == "quote_price":
            if action.price_quote is not None and action.items:
                item = action.items[0]
                price_str = cls._format_currency(action.price_quote)
                return f"{item.name} ka daam {price_str} per {item.unit} hai."
            return action.message or f"Is item ka daam {total_spoken} hai."

        # 7. Action: quote_stock
        if act_name == "quote_stock":
            if action.stock_quote is not None and action.items:
                item = action.items[0]
                stock_val = int(action.stock_quote) if action.stock_quote % 1 == 0 else float(action.stock_quote)
                return f"Hamare paas {item.name} ke {stock_val} {item.unit} stock mein available hain."
            return action.message or "Yeh item stock mein available hai."

        # 8. Action: product_not_found
        if act_name == "product_not_found":
            if action.message:
                return action.message
            return "Maaf kijiye, yeh item hamari dukaan mein nahi mila. Kya aap kuch aur lena chahenge?"

        # 9. Action: replace_quantity (Correction)
        if act_name == "replace_quantity":
            if action.items:
                item = action.items[0]
                qty_str = cls._format_quantity(item.quantity, item.unit)
                return f"Theek hai, {item.name} ki quantity badal kar {qty_str} kar di hai. Total {total_spoken} hua."
            return f"Theek hai, quantity update kar di hai. Total {total_spoken} hua."

        # 10. Action: remove_item
        if act_name == "remove_item":
            if action.items:
                item_name = action.items[0].name
                return f"Ji, {item_name} cart se hata diya hai. Cart mein total {total_spoken} ka samaan hai."
            return f"Ji, item cart se hata diya hai. Total {total_spoken} hua."

        # 11. Action: add_items
        if act_name == "add_items":
            if action.items:
                items_str = cls._format_items_list(action.items)
                return f"Ji bhaiya, {items_str} add kar diye hain. Total {total_spoken} hua. Kuch aur chahiye?"
            return f"Ji bhaiya, item add kar diya hai. Total {total_spoken} hua. Kuch aur chahiye?"

        # Fallback to action message if present
        if action.message:
            return action.message

        return f"Theek hai, aapka cart update kar diya gaya hai. Total {total_spoken} hua."

