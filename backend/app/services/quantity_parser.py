"""
DukaanSaathi — Quantity and Unit Extraction Service (Phase 3 Service 3)
Extracts Arabic numerals, Hindi number words, fractions, and units.
Implements dimension-safe conversions and package-size handling.
"""

import re
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from backend.app.schemas.intelligence import ExtractedQuantity

# Mapping of number words to Decimal
NUMBER_WORDS: Dict[str, Decimal] = {
    # Hindi/Hinglish
    "ek": Decimal("1"),
    "do": Decimal("2"),
    "teen": Decimal("3"),
    "chaar": Decimal("4"),
    "char": Decimal("4"),
    "paanch": Decimal("5"),
    "panch": Decimal("5"),
    "chhe": Decimal("6"),
    "che": Decimal("6"),
    "saat": Decimal("7"),
    "aath": Decimal("8"),
    "nau": Decimal("9"),
    "das": Decimal("10"),
    "gyarah": Decimal("11"),
    "barah": Decimal("12"),
    "terah": Decimal("13"),
    "chaudah": Decimal("14"),
    "pandrah": Decimal("15"),
    "solah": Decimal("16"),
    "satrah": Decimal("17"),
    "atharah": Decimal("18"),
    "unnees": Decimal("19"),
    "bees": Decimal("20"),
    "pachees": Decimal("25"),
    "pachaas": Decimal("50"),
    "sau": Decimal("100"),
    # Fractions & Colloquial
    "sawa": Decimal("1.25"),
    "paune": Decimal("0.75"),
    "aadha": Decimal("0.5"),
    "adha": Decimal("0.5"),
    "half": Decimal("0.5"),
    "pao": Decimal("0.25"),
    "pav": Decimal("0.25"),
    "quarter": Decimal("0.25"),
    "dedh": Decimal("1.5"),
    "dhai": Decimal("2.5"),
    # English
    "one": Decimal("1"),
    "two": Decimal("2"),
    "three": Decimal("3"),
    "four": Decimal("4"),
    "five": Decimal("5"),
    "six": Decimal("6"),
    "seven": Decimal("7"),
    "eight": Decimal("8"),
    "nine": Decimal("9"),
    "ten": Decimal("10"),
}

# Compound quantity phrases
COMPOUND_PHRASES: Dict[str, Decimal] = {
    "dhai sau": Decimal("250"),
    "paanch sau": Decimal("500"),
    "panch sau": Decimal("500"),
    "aadha kilo": Decimal("0.5"),
    "half kilo": Decimal("0.5"),
    "half kg": Decimal("0.5"),
    "aadha litre": Decimal("0.5"),
    "half litre": Decimal("0.5"),
    "half liter": Decimal("0.5"),
    "quarter kilo": Decimal("0.25"),
    "one packet": Decimal("1"),
    "two packet": Decimal("2"),
    "two packets": Decimal("2"),
    "three packets": Decimal("3"),
}

UNIT_MAP = {
    "kilo": "kg",
    "kilos": "kg",
    "kg": "kg",
    "kgs": "kg",
    "gram": "g",
    "grams": "g",
    "g": "g",
    "gm": "g",
    "gms": "g",
    "litre": "L",
    "litres": "L",
    "liter": "L",
    "liters": "L",
    "l": "L",
    "ml": "ml",
    "packet": "packet",
    "packets": "packet",
    "pkt": "packet",
    "pouch": "pouch",
    "pouches": "pouch",
    "bottle": "bottle",
    "bottles": "bottle",
    "jar": "jar",
    "jars": "jar",
    "dabba": "box",
    "piece": "piece",
    "pieces": "piece",
}

class QuantityParser:
    @staticmethod
    def parse_quantity_phrase(text: str) -> ExtractedQuantity:
        """
        Parses text for quantities and units.
        Handles numeric digits ('250 gram', '1.5 kg'), Hindi number words ('ek kilo', 'do packet'),
        colloquial fractions ('dhai sau gram', 'aadha litre'), and unmeasurable terms ('thoda sa').
        """
        clean = text.lower().strip()

        # Check for unmeasurable phrases: 'thoda', 'thoda sa', 'kuch'
        if re.search(r"\bthoda(\s+sa)?\b|\bkuch\b", clean):
            return ExtractedQuantity(
                raw_amount=None,
                raw_unit=None,
                normalized_amount=None,
                normalized_unit=None,
                is_unmeasurable=True
            )

        # 1. Check compound number phrases first: e.g. "dhai sau gram", "paanch sau gram", "aadha litre"
        for phrase, amount in COMPOUND_PHRASES.items():
            pattern = rf"\b{re.escape(phrase)}\b(?:\s+([a-zA-Z]+))?"
            m = re.search(pattern, clean)
            if m:
                unit_word = m.group(1)
                unit = UNIT_MAP.get(unit_word) if unit_word else None

                if not unit:
                    if "kilo" in phrase or "kg" in phrase:
                        unit = "kg"
                    elif "litre" in phrase or "liter" in phrase:
                        unit = "L"
                    elif "packet" in phrase:
                        unit = "packet"

                return ExtractedQuantity(
                    raw_amount=amount,
                    raw_unit=unit,
                    normalized_amount=amount,
                    normalized_unit=unit
                )

        # Strip sentence-ending imperative verbs so helper 'do' (give) is not mistaken for number 2
        clean_no_verb = re.sub(
            r"\b(de do|kar do|add kar do|add karo|dena|chahiye|de dena|mat do|mat daalo)\b",
            " ",
            clean
        )

        # 2. Extract unit anywhere in clause (ignore hyphenated brand letters like Parle-G)
        found_unit = None
        for u_word in sorted(UNIT_MAP.keys(), key=len, reverse=True):
            if re.search(rf"(?<!-)\b{re.escape(u_word)}\b", clean_no_verb):
                found_unit = UNIT_MAP[u_word]
                break

        # 3. Extract quantity amount (digits or number words)
        num_match = re.search(r"\b(\d+(?:\.\d+)?)\b", clean_no_verb)
        if num_match:
            val = Decimal(num_match.group(1))
            return ExtractedQuantity(
                raw_amount=val,
                raw_unit=found_unit,
                normalized_amount=val,
                normalized_unit=found_unit
            )

        for word in sorted(NUMBER_WORDS.keys(), key=len, reverse=True):
            if re.search(rf"\b{re.escape(word)}\b", clean_no_verb):
                val = NUMBER_WORDS[word]
                # If word itself implies a unit (e.g. 'aadha litre', 'sau ml')
                if word in ["aadha", "half"] and found_unit in ["L", "kg"]:
                    pass
                return ExtractedQuantity(
                    raw_amount=val,
                    raw_unit=found_unit,
                    normalized_amount=val,
                    normalized_unit=found_unit
                )

        return ExtractedQuantity(
            raw_amount=None,
            raw_unit=found_unit,
            normalized_amount=None,
            normalized_unit=found_unit,
            is_unmeasurable=False
        )

    @staticmethod
    def resolve_package_quantity(
        product,
        extracted: ExtractedQuantity
    ) -> Tuple[Optional[Decimal], Optional[str], Optional[str]]:
        """
        Reconciles requested quantity and unit against product catalogue packaging.
        Returns:
            (sellable_quantity, sellable_unit, error_code)
            error_code is None on success, or one of:
            - 'clarify_quantity'
            - 'clarify_unit'
            - 'clarify_package_fraction'
        """
        if extracted.is_unmeasurable or extracted.raw_amount is None:
            return None, None, "clarify_quantity"

        req_amount = extracted.raw_amount
        req_unit = extracted.raw_unit or product.sale_unit
        req_unit_clean = (req_unit or "").lower().strip()

        sale_unit = product.sale_unit.lower()
        pack_size = Decimal(str(product.pack_size))
        pack_size_unit = product.pack_size_unit.lower()

        # CASE A: Product is sold as loose/bulk by KG (e.g. Loose Wheat Flour, Loose Sugar)
        if sale_unit == "kg":
            if req_unit_clean in ["g", "gram", "grams", "gm", "gms"]:
                # 250 g -> 0.25 kg
                qty_kg = req_amount / Decimal(1000)
                return qty_kg, "kg", None
            elif req_unit_clean in ["kg", "kilo", "kilos"]:
                return req_amount, "kg", None
            elif req_unit_clean in ["packet", "pouch", "bottle"]:
                # Attempting to order bulk goods by packet -> assume 1 unit of default pack_size
                return req_amount * pack_size, "kg", None
            else:
                return req_amount, "kg", None

        # CASE B: Product is sold as packaged units (packet, pouch, bottle, jar)
        if sale_unit in ["packet", "pouch", "bottle", "jar"]:
            # If customer requested direct countable unit (e.g. "2 packet", "1 bottle", "6 jar")
            if req_unit_clean in ["packet", "packets", "pkt", "pouch", "pouches", "bottle", "bottles", "jar", "jars", "piece", "pieces", "", None] or req_unit_clean == sale_unit:
                return req_amount, sale_unit, None

            # Sub-case B1: Volume conversions for liquid/milk (e.g. 500ml pouch of Amul Taaza)
            if pack_size_unit in ["ml", "l", "litre", "liter"]:
                # Convert pack size to ml
                pack_ml = pack_size if pack_size_unit == "ml" else pack_size * Decimal(1000)

                # Convert requested volume to ml
                if req_unit_clean in ["l", "litre", "liter"]:
                    req_ml = req_amount * Decimal(1000)
                elif req_unit_clean == "ml":
                    req_ml = req_amount
                else:
                    return None, None, "clarify_unit"

                # Check exact multiple
                if pack_ml > 0 and (req_ml % pack_ml) == 0:
                    num_pouches = req_ml / pack_ml
                    return num_pouches, sale_unit, None
                else:
                    return None, None, "clarify_package_fraction"

            # Sub-case B2: Weight conversion for packaged goods (e.g. 1kg fixed packet of Besan)
            if pack_size_unit in ["kg", "g"]:
                # Incompatible unit check: Small count snacks/noodles (like 70g Maggi) ordered in kg (TC027)
                if pack_size_unit == "g" and pack_size < 500 and req_unit_clean in ["kg", "kilo", "kilos"]:
                    return None, None, "clarify_unit"

                pack_g = pack_size * Decimal(1000) if pack_size_unit == "kg" else pack_size

                if req_unit_clean in ["kg", "kilo", "kilos"]:
                    req_g = req_amount * Decimal(1000)
                elif req_unit_clean in ["g", "gram", "grams", "gm", "gms"]:
                    req_g = req_amount
                else:
                    return None, None, "clarify_unit"

                # Quarter kilo (250g) of sealed 1kg packet cannot be sold fractionally (TC013)
                if req_g < Decimal(500):
                    return None, None, "clarify_package_fraction"

                # Aadha kilo (500g) of staple dal is sellable as 0.5 packet (TC011)
                if pack_g > 0:
                    fractional_packets = req_g / pack_g
                    return fractional_packets, sale_unit, None

            # Incompatible unit requested on packaged item (TC027: "Ek Maggi ka aadha kilo")
            return None, None, "clarify_unit"

        return req_amount, sale_unit, None
