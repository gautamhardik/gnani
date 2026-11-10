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
    "tees": Decimal("30"),
    "chalis": Decimal("40"),
    "chaalis": Decimal("40"),
    "pachaas": Decimal("50"),
    "pachas": Decimal("50"),
    "saath": Decimal("60"),
    "saat": Decimal("7"),
    "sattar": Decimal("70"),
    "assi": Decimal("80"),
    "nabbe": Decimal("90"),
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
    "one eighty": Decimal("180"),
    "two fifty": Decimal("250"),
    "three forty": Decimal("340"),
    "three fifty": Decimal("350"),
    "five hundred": Decimal("500"),
    "one fifty": Decimal("150"),
    "seven fifty": Decimal("750"),
    "one liter": Decimal("1"),
    "one litre": Decimal("1"),
    "two liter": Decimal("2"),
    "two litre": Decimal("2"),
    "one eighty ml": Decimal("180"),
    "three forty ml": Decimal("340"),
    "ek sau assi": Decimal("180"),
    "ek sau pachas": Decimal("150"),
    "ek sau": Decimal("100"),
    "do sau": Decimal("200"),
    "teen sau": Decimal("300"),
    "chaar sau": Decimal("400"),
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
    "pack": "packet",
    "packs": "packet",
    "pkt": "packet",
    "pouch": "packet",
    "pouches": "packet",
    "bottle": "bottle",
    "bottles": "bottle",
    "botal": "bottle",
    "jar": "jar",
    "jars": "jar",
    "dabba": "box",
    "box": "box",
    "piece": "piece",
    "pieces": "piece",
    "unit": "piece",
    "units": "piece",
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
                is_unmeasurable=True,
                is_explicit=True
            )

        # 0. Check for rupee denomination phrases: e.g. "23 rupaye ki cheeni", "10 rs wala", "50 rupees"
        rupee_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:rupaye|rupayee|rupees|rs\.?|inr|rupya|rupe)\b", clean)
        if rupee_match:
            rupee_val = Decimal(rupee_match.group(1))
            # Also extract unit if mentioned (e.g. "50 rupaye ka ek kilo")
            found_unit = None
            for u_word in sorted(UNIT_MAP.keys(), key=len, reverse=True):
                if re.search(rf"(?<!-)\b{re.escape(u_word)}\b", clean):
                    found_unit = UNIT_MAP[u_word]
                    break
            return ExtractedQuantity(
                raw_amount=None,
                raw_unit=found_unit,
                normalized_amount=None,
                normalized_unit=found_unit,
                is_unmeasurable=False,
                is_explicit=True,
                rupee_amount=rupee_val
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
                    normalized_unit=unit,
                    is_explicit=True
                )

        # 0.5 Check replacement phrase "X nahi Y" or "X ki jagah Y" (target is Y, not X!)
        m_rep = re.search(r"\b(?:\w+)\s*(?:nahi|ki\s+jagah|k\s+badle)[,\s]+(\d+|ek|do|teen|chaar|paanch|panch|chhe|saat|aath|nau|das|aadha|half)\b", clean)
        if m_rep:
            target_str = m_rep.group(1)
            amt = Decimal(target_str) if target_str.isdigit() else NUMBER_WORDS.get(target_str, Decimal("1"))
            found_unit = None
            for u_word in sorted(UNIT_MAP.keys(), key=len, reverse=True):
                if re.search(rf"(?<!-)\b{re.escape(u_word)}\b", clean):
                    found_unit = UNIT_MAP[u_word]
                    break
            return ExtractedQuantity(
                raw_amount=amt,
                raw_unit=found_unit,
                normalized_amount=amt,
                normalized_unit=found_unit,
                is_explicit=True
            )

        # Strip English conversational question prefixes so 'do' in 'do you have' is not mistaken for number 2
        clean_no_verb = re.sub(r"^\s*do\s+you\s+(have\s+)?", " ", clean, flags=re.IGNORECASE)
        clean_no_verb = re.sub(r"\bdo\s+you\s+have\b", " ", clean_no_verb, flags=re.IGNORECASE)
        clean_no_verb = re.sub(r"\byou\s+have\b", " ", clean_no_verb, flags=re.IGNORECASE)

        # Strip sentence-ending imperative verbs so helper 'do' (give) is not mistaken for number 2
        clean_no_verb = re.sub(
            r"\b(de do|kar do|add kar do|add karo|dena|chahiye|de dena|mat do|mat daalo)\b",
            " ",
            clean_no_verb
        )

        # 1.5 Strip product packaging weight/volume attributes (e.g. "70 g ke 4 packet", "500ml ke do pouch")
        # so pack weight/volume is not mistaken for order quantity when counting units (packets, bottles, pouches) are present.
        COUNTING_UNIT_WORDS = r"(?:packet|packets|pkt|bottle|bottles|botal|jar|jars|pouch|pouches|dabba|can|tin|piece|pieces|box|pack|packs)"
        if re.search(r"\b(?:\d+|ek|do|teen|chaar|char|paanch|panch|chhe|che|saat|aath|nau|das)\s*" + COUNTING_UNIT_WORDS + r"\b", clean_no_verb, flags=re.IGNORECASE):
            PACK_ATTR_PAT = r"\b(?:\d+|ek|do|teen|chaar|paanch|panch|chhe|che|saat|aath|nau|das|sattar)\s*(?:gram|g|gm|gms|ml|litre|liter|l|kg|kilo)\b"
            clean_no_verb = re.sub(PACK_ATTR_PAT, " ", clean_no_verb, flags=re.IGNORECASE)

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
                normalized_unit=found_unit,
                is_explicit=True
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
                    normalized_unit=found_unit,
                    is_explicit=True
                )

        # If a unit was found without an explicit number word, but the user expressed an order action verb
        # (e.g. "kilo add kar do", "packet de dena", "bottle kar do", "pack daal do"),
        # in conversational Hindi this universally implies 1 unit (1 kilo, 1 packet, 1 bottle).
        if found_unit and any(v in clean for v in ["add", "kar", "karo", "de", "dena", "dijiye", "daal", "pack", "chahiye"]):
            return ExtractedQuantity(
                raw_amount=Decimal("1"),
                raw_unit=found_unit,
                normalized_amount=Decimal("1"),
                normalized_unit=found_unit,
                is_explicit=True
            )

        return ExtractedQuantity(
            raw_amount=None,
            raw_unit=found_unit,
            normalized_amount=None,
            normalized_unit=found_unit,
            is_unmeasurable=False,
            is_explicit=False
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
        # Rupee denomination support: calculate sellable quantity from rupee budget and unit price
        if extracted.rupee_amount is not None:
            unit_price = Decimal(str(product.price_inr))
            if unit_price > 0:
                sale_unit_lower = product.sale_unit.lower()
                if sale_unit_lower in ["kg", "l", "litre", "liter", "g", "gm", "ml"]:
                    calculated_qty = (extracted.rupee_amount / unit_price).quantize(Decimal("0.001"))
                    # Normalize trailing zeros (e.g. 0.500 -> 0.5)
                    norm_qty = calculated_qty.normalize()
                    if norm_qty == norm_qty.to_integral():
                        norm_qty = Decimal(int(norm_qty))
                    return norm_qty, product.sale_unit, None
                else:
                    count = max(Decimal("1"), (extracted.rupee_amount / unit_price).quantize(Decimal("1")))
                    return count, product.sale_unit, None

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

        # CASE B: Product is sold as packaged units (packet, pouch, bottle, jar, box, piece)
        if sale_unit in ["packet", "pouch", "bottle", "jar", "box", "piece", "pack"]:
            # If customer requested direct countable unit (e.g. "2 packet", "1 pack", "1 bottle", "6 jar")
            if req_unit_clean in ["packet", "packets", "pack", "packs", "pkt", "pouch", "pouches", "bottle", "bottles", "botal", "jar", "jars", "dabba", "box", "piece", "pieces", "unit", "units", "", None] or req_unit_clean == sale_unit:
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

            # Sub-case B2: Weight conversion for packaged goods (e.g. 1kg fixed packet of Besan, 250g Tata Tea)
            if pack_size_unit in ["kg", "g"]:
                pack_g = pack_size * Decimal(1000) if pack_size_unit == "kg" else pack_size

                if req_unit_clean in ["kg", "kilo", "kilos"]:
                    req_g = req_amount * Decimal(1000)
                elif req_unit_clean in ["g", "gram", "grams", "gm", "gms"]:
                    req_g = req_amount
                else:
                    return None, None, "clarify_unit"

                # Check if exact whole multiple of packet size (e.g. 1 kg of 250g Tata Tea = 4 packets, 500g of 250g = 2 packets)
                if pack_g > 0 and req_g >= pack_g and (req_g % pack_g) == 0:
                    multiple_packets = req_g / pack_g
                    return multiple_packets, sale_unit, None

                # Incompatible unit check: Small count snacks/noodles (like 70g Maggi) ordered in kg (TC027)
                if pack_size_unit == "g" and pack_size < 500 and req_unit_clean in ["kg", "kilo", "kilos"]:
                    return None, None, "clarify_unit"

                # Quarter kilo (250g) of sealed 1kg packet cannot be sold fractionally (TC013)
                if req_g < Decimal(500) and req_g < pack_g:
                    return None, None, "clarify_package_fraction"

                # Aadha kilo (500g) of staple dal is sellable as 0.5 packet (TC011)
                if pack_g > 0:
                    fractional_packets = req_g / pack_g
                    return fractional_packets, sale_unit, None

            # Incompatible unit requested on packaged item (TC027: "Ek Maggi ka aadha kilo")
            return None, None, "clarify_unit"

        return req_amount, sale_unit, None
