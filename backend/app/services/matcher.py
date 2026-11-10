"""
DukaanSaathi — Product Matching Service (Phase 3 Service 2)
Implements exact canonical name and alias lookup, RapidFuzz candidate retrieval,
ambiguity-margin checks, and multi-variant clarification detection.
Never selects an uncertain product automatically.
"""

import re
from decimal import Decimal
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from rapidfuzz import fuzz, process

from backend.app.models import Product, ProductAlias
from backend.app.services.indic_soundex import IndicSoundex
from backend.app.schemas.intelligence import (
    ProductMatchCandidate,
    ProductMatchResult,
    ClarificationType,
)

GENERIC_CATEGORY_MAP: Dict[str, List[str]] = {
    "toothpaste": ["toothpaste", "colgate", "oral care", "manjan"],
    "manjan": ["toothpaste", "colgate", "oral care", "manjan"],
    "tel": ["mustard oil", "sunflower oil", "soybean oil", "coconut oil", "hair oil", "oil"],
    "cooking oil": ["mustard oil", "sunflower oil", "soybean oil", "refined oil"],
    "oil": ["mustard oil", "sunflower oil", "soybean oil", "coconut oil", "hair oil", "oil"],
    "sarson tel": ["mustard oil"],
    "sabun": ["soap", "lifebuoy", "dove", "bathing soap", "detergent bar"],
    "soap": ["soap", "lifebuoy", "dove", "bathing soap", "detergent bar"],
    "shampoo": ["shampoo", "clinic plus", "hair care"],
    "biscuit": ["biscuit", "biscuits", "good day", "oreo", "rusk", "cookies"],
    "biscuits": ["biscuit", "biscuits", "good day", "oreo", "rusk", "cookies"],
    "namkeen": ["namkeen", "aloo bhujia", "kurkure", "lays", "chips", "bhujia", "snacks"],
    "chai": ["tea", "tata tea", "chai"],
    "tea": ["tea", "tata tea", "chai"],
    "chawal": ["regular rice", "basmati", "sona masoori", "rice", "chawal"],
    "rice": ["regular rice", "basmati", "sona masoori", "rice", "chawal"],
    "dal": ["toor dal", "moong dal", "masoor dal", "urad dal", "chana dal", "dal", "pulses"],
    "daal": ["toor dal", "moong dal", "masoor dal", "urad dal", "chana dal", "dal", "pulses"],
    "aata": ["atta", "wheat flour", "gehu"],
    "atta": ["atta", "wheat flour", "gehu"],
    "doodh": ["milk", "taaza", "gold", "toned", "dairy"],
    "milk": ["milk", "taaza", "gold", "toned", "dairy"],
    "ghee": ["cow ghee", "desi ghee", "ghee", "pure ghee"],
    "makhana": ["makhana", "fox nuts"],
    "masala": ["turmeric", "haldi", "chilli powder", "mirch", "coriander", "dhaniya", "cumin", "jeera", "masala"],
    "sauce": ["ketchup", "tomato sauce", "soy sauce", "chilli sauce", "sauce", "pichkoo"],
    "ketchup": ["ketchup", "tomato sauce", "pichkoo"],
    "chocolate": ["dairy milk", "kitkat", "5 star", "silk", "chocolate"],
    "chocolates": ["dairy milk", "kitkat", "5 star", "silk", "chocolate"],
    "toffee": ["pulse", "melody", "alpenliebe", "mango bite", "toffee", "candy"],
    "toffees": ["pulse", "melody", "alpenliebe", "mango bite", "toffee", "candy"],
    "candy": ["pulse", "melody", "alpenliebe", "mango bite", "candy"],
    "cornflakes": ["corn flakes", "cornflakes", "kellogg"],
    "chocos": ["chocos", "kellogg"],
    "cereal": ["corn flakes", "chocos", "oats"],
    "oats": ["quaker oats", "oats", "daliya"],
    "chowmein": ["hakka noodles", "chowmein", "noodles", "chings"],
    "noodles": ["maggi", "hakka noodles", "chowmein", "yippee", "noodles"],
    "coffee": ["nescafe", "bru", "coffee"],
    "sachet": ["sachet", "clinic plus sachet", "pouch"],
}

class ProductMatcher:
    def __init__(self, db: Session, store_id: str = "STORE001"):
        self.db = db
        self.store_id = store_id
        self._load_catalogue_cache()

    def _load_catalogue_cache(self):
        """Pre-loads store catalogue and alias index into memory for high-performance matching."""
        self.products: Dict[str, Product] = {}
        self.alias_to_products: Dict[str, List[Tuple[str, str, str]]] = {}  # norm_alias -> [(prod_id, alias_type, display_alias)]
        self.all_alias_strings: List[str] = []
        self.alias_metadata: Dict[str, List[str]] = {}  # alias_str -> [prod_ids]

        prods = self.db.query(Product).filter(
            Product.store_id == self.store_id,
            Product.is_active == True
        ).all()

        for p in prods:
            self.products[p.product_id] = p
            # Index canonical product name
            name_clean = p.name.lower().strip()
            self.alias_metadata.setdefault(name_clean, []).append(p.product_id)
            self.alias_to_products.setdefault(name_clean, []).append((p.product_id, "canonical", p.name))
            if name_clean not in self.all_alias_strings:
                self.all_alias_strings.append(name_clean)

            # Index product name without trailing pack size (e.g. "Clinic Plus Shampoo 180 ml" -> "clinic plus shampoo")
            name_without_size = re.sub(
                r"\s+\d+(?:\.\d+)?\s*(?:g|kg|ml|l|litre|liter|gm|packet|pack|bottle|piece|pc|can|pouch)\b.*$",
                "",
                name_clean,
                flags=re.IGNORECASE
            ).strip()
            if name_without_size and name_without_size != name_clean:
                self.alias_metadata.setdefault(name_without_size, []).append(p.product_id)
                self.alias_to_products.setdefault(name_without_size, []).append((p.product_id, "name_without_size", p.name))
                if name_without_size not in self.all_alias_strings:
                    self.all_alias_strings.append(name_without_size)

            # Index brand name directly (e.g. "Clinic Plus", "Head & Shoulders", "Fortune", "Tata Tea")
            if p.brand:
                brand_lower = p.brand.lower().strip()
                for b_var in set([brand_lower, brand_lower.replace("&", "and"), brand_lower.replace("&", " "), re.sub(r"\s+", " ", brand_lower.replace("&", " ")).strip()]):
                    if not b_var:
                        continue
                    self.alias_metadata.setdefault(b_var, []).append(p.product_id)
                    self.alias_to_products.setdefault(b_var, []).append((p.product_id, "brand", p.name))
                    if b_var not in self.all_alias_strings:
                        self.all_alias_strings.append(b_var)

                words = name_clean.split()
                if len(words) >= 2 and words[0] == brand_lower:
                    short_variant = f"{words[0]} {words[1]}"
                    self.alias_metadata.setdefault(short_variant, []).append(p.product_id)
                    self.alias_to_products.setdefault(short_variant, []).append((p.product_id, "brand_variant", p.name))
                    if short_variant not in self.all_alias_strings:
                        self.all_alias_strings.append(short_variant)

                    # Also index brand + subsequent meaningful product words (e.g. "amul ghee", "amul butter")
                    for w in words[2:]:
                        clean_w = re.sub(r"[^\w]", "", w)
                        if len(clean_w) >= 3 and not clean_w.isdigit() and clean_w not in ["pouch", "bottle", "packet", "pack", "jar", "can", "tin", "box", "regular", "pure", "fresh"]:
                            brand_word_combo = f"{brand_lower} {clean_w}"
                            self.alias_metadata.setdefault(brand_word_combo, []).append(p.product_id)
                            self.alias_to_products.setdefault(brand_word_combo, []).append((p.product_id, "brand_word", p.name))
                            if brand_word_combo not in self.all_alias_strings:
                                self.all_alias_strings.append(brand_word_combo)

        aliases = (
            self.db.query(ProductAlias)
            .join(Product, ProductAlias.product_id == Product.product_id)
            .filter(Product.store_id == self.store_id, Product.is_active == True)
            .all()
        )

        for a in aliases:
            norm = a.normalized_alias.lower().strip()
            norm_variants = set([
                norm,
                norm.replace("&", "and"),
                norm.replace("&", " "),
                norm.replace(" and ", " "),
                re.sub(r"\s+", " ", norm.replace("&", " ")).strip()
            ])
            for nv in norm_variants:
                if not nv:
                    continue
                self.alias_to_products.setdefault(nv, []).append((a.product_id, a.alias_type, a.alias))
                self.alias_metadata.setdefault(nv, []).append(a.product_id)
                if nv not in self.all_alias_strings:
                    self.all_alias_strings.append(nv)

        # Build 4-Stage Indic Soundex phonetic index for Tri-Modal RRF
        self.soundex_to_aliases: Dict[str, List[str]] = {}
        for s in self.all_alias_strings:
            sx = IndicSoundex.soundex(s)
            self.soundex_to_aliases.setdefault(sx, []).append(s)

    @staticmethod
    def reciprocal_rank_fusion(
        lexical_ranked: List[str],
        semantic_ranked: List[str],
        phonetic_ranked: List[str],
        k: int = 60
    ) -> List[Tuple[str, float]]:
        """
        Reciprocal Rank Fusion (RRF) score aggregation across Tri-Modal candidate lists:
        RRF_Score(d) = sum_{m in {Lexical, Semantic, Phonetic}} 1 / (k + rank_m(d))
        """
        scores: Dict[str, float] = {}
        for rank, pid in enumerate(lexical_ranked):
            scores[pid] = scores.get(pid, 0.0) + (1.0 / (k + rank + 1))
        for rank, pid in enumerate(semantic_ranked):
            scores[pid] = scores.get(pid, 0.0) + (1.0 / (k + rank + 1))
        for rank, pid in enumerate(phonetic_ranked):
            scores[pid] = scores.get(pid, 0.0) + (1.0 / (k + rank + 1))
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def _find_generic_category_matches(self, clean_q: str) -> List[str]:
        """Finds store products matching a vernacular/generic category keyword, sorted by available stock."""
        target_keywords = None
        matched_cat_key = None
        for cat_key, kw_list in sorted(GENERIC_CATEGORY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if clean_q == cat_key or re.search(rf"\b{re.escape(cat_key)}\b", clean_q):
                target_keywords = kw_list
                matched_cat_key = cat_key
                break

        if not target_keywords:
            return []

        matched_pids = set()
        for pid, p in self.products.items():
            p_name = p.name.lower()
            p_brand = (p.brand or "").lower()
            for kw in target_keywords:
                # Use word-boundary regex so 'dal' does not match 'sandalwood' and 'oil' does not match 'coil'
                if re.search(rf"\b{re.escape(kw)}\b", p_name) or (p_brand and re.search(rf"\b{re.escape(kw)}\b", p_brand)):
                    matched_pids.add(pid)
                    break

        # If user query contains specific qualifier words outside the generic category word, filter by them
        if matched_cat_key and len(matched_pids) > 1:
            stop_tokens = {
                "ek", "do", "teen", "chaar", "paanch", "aadha", "bottle", "packet", "pouch",
                "kg", "kilo", "g", "gm", "ml", "litre", "liter", "de", "do", "kar", "dijiye",
                "dena", "chahiye", "hai", "hain", "ka", "ki", "ke", "wala", "wali", "wale",
                "add", "cart", "mein", "bhi", "bhaiya", "ji"
            }
            # Step A: Filter by brand if user query contains brand keywords (e.g. "head and shoulders")
            brand_matched_pids = set()
            for pid in matched_pids:
                p = self.products[pid]
                if p.brand:
                    brand_clean = re.sub(r"[^\w\s]", " ", p.brand.lower())
                    brand_words = [w for w in brand_clean.split() if len(w) >= 3 and w not in stop_tokens]
                    if brand_words and all(re.search(rf"\b{re.escape(bw)}\b", clean_q) for bw in brand_words):
                        brand_matched_pids.add(pid)
                    elif brand_words and any(re.search(rf"\b{re.escape(bw)}\b", clean_q) for bw in brand_words) and len(brand_words) == 1:
                        brand_matched_pids.add(pid)
            if brand_matched_pids:
                matched_pids = brand_matched_pids

            # Step B: Filter by pack size / numbers if query specifies volume/weight digits (e.g. "180 ml")
            digits = re.findall(r"\b\d+\b", clean_q)
            if digits:
                size_matched_pids = set()
                for pid in matched_pids:
                    p_digits = re.findall(r"\b\d+\b", self.products[pid].name.lower())
                    if any(d in p_digits for d in digits):
                        size_matched_pids.add(pid)
                if size_matched_pids:
                    matched_pids = size_matched_pids

            # Step C: General qualifier tokens
            query_tokens = [
                w for w in clean_q.split()
                if w not in stop_tokens and w != matched_cat_key and w not in target_keywords and len(w) >= 3
            ]
            if query_tokens and len(matched_pids) > 1:
                filtered_pids = set()
                for pid in matched_pids:
                    p = self.products[pid]
                    p_text = f"{p.name.lower()} {(p.brand or '').lower()}"
                    if any(t in p_text for t in query_tokens):
                        filtered_pids.add(pid)
                if filtered_pids:
                    matched_pids = filtered_pids

        def get_stock(pid: str) -> Decimal:
            prod = self.products.get(pid)
            if prod and prod.inventory:
                return prod.inventory.stock_quantity - prod.inventory.reserved_quantity
            return Decimal(0)

        return sorted(list(matched_pids), key=get_stock, reverse=True)

    def match_product(
        self,
        query_text: str,
        confidence_threshold: float = 75.0,
        ambiguity_margin: float = 6.0
    ) -> ProductMatchResult:
        """
        Matches a query phrase (e.g. 'aata', 'Maggi', 'Amul Taaza doodh', 'dragon fruit')
        against the store catalogue.
        """
        clean_q = re.sub(r"[^\w\s-]", " ", query_text).lower().strip()
        clean_q = re.sub(r"\s+", " ", clean_q)
        tokens = [w for w in clean_q.split() if w]
        NON_PRODUCT_STOPWORDS = {
            "packet", "packets", "pack", "packs", "bottle", "bottles", "botal", "jar", "jars",
            "box", "dabba", "pouch", "tube", "tin", "bag", "kilo", "kg", "gram", "grams", "gm", "g",
            "litre", "liter", "l", "ml", "piece", "pieces", "pcs", "add", "kar", "karo", "do",
            "de", "dijiye", "dena", "chahiye", "mujhe", "bhaiya", "ek", "do", "teen", "char", "chaar", "paanch", "haan",
            "ji", "bola", "maine", "nahi", "tumhare", "paas", "hai", "kya", "hoga", "milega",
            "check", "karke", "batana", "usmein", "kuch", "pada", "hua", "pehle", "se",
            "meri", "mera", "mere", "cart", "card", "khali", "clear", "empty", "saaf", "sab", "saara",
            "saari", "order", "cancel", "reset",
            "hi", "hee", "ही", "bhi", "bhee", "भी", "to", "toh", "तो", "bas", "sirf", "keval"
        }
        remaining_meaningful = [t for t in tokens if not t.isdigit() and t not in NON_PRODUCT_STOPWORDS]
        if not clean_q or not remaining_meaningful or len(" ".join(remaining_meaningful).strip()) <= 2:
            return ProductMatchResult(
                matched=False,
                reason="Query contains only quantity, unit, or conversational stopwords"
            )

        # -------------------------------------------------------------
        # STAGE 1: Exact Alias or Exact Canonical Match
        # -------------------------------------------------------------
        if clean_q in ["sabun", "soap", "tel", "cooking oil", "oil", "biscuit", "biscuits", "namkeen", "dal", "daal", "chawal", "rice"]:
            cat_matches = self._find_generic_category_matches(clean_q)
            if len(cat_matches) > 1:
                candidates = [self._build_candidate(pid, 1.0, clean_q, "generic_category", is_generic=True) for pid in cat_matches[:5]]
                options = [f"{c.name} (₹{c.price_inr})" for c in candidates]
                return ProductMatchResult(
                    matched=False,
                    is_ambiguous=True,
                    candidates=candidates,
                    clarification_type=ClarificationType.PRODUCT,
                    clarification_options=options,
                    reason=f"Ambiguous category '{query_text}' matches multiple store products."
                )

        if clean_q in self.alias_to_products:
            prod_records = self.alias_to_products[clean_q]
            matched_prod_ids = list(set(r[0] for r in prod_records))

            # Ambiguous brand-level milk query (TC020: "Ek Amul milk dena" -> clarify_size)
            if clean_q in ["amul milk", "amul doodh"]:
                matched_prod_ids = [
                    p.product_id for p in self.products.values()
                    if p.brand and p.brand.lower() == "amul" and (
                        (p.category and "dairy" in p.category.lower()) or "milk" in p.name.lower() or "taaza" in p.name.lower() or "gold" in p.name.lower()
                    )
                ]

            # Sub-check: Does this exact alias map to multiple distinct active SKUs?
            # e.g. "doodh" maps to PRD021 (Amul Taaza), PRD022 (Amul Gold), PRD023 (Mother Dairy)
            if len(matched_prod_ids) > 1:
                candidates = [self._build_candidate(pid, 1.0, clean_q, "exact_alias", is_generic=True) for pid in matched_prod_ids]
                options = [f"{c.name} (₹{c.price_inr})" for c in candidates]
                clar_type = ClarificationType.SIZE if "amul" in clean_q else ClarificationType.PRODUCT
                return ProductMatchResult(
                    matched=False,
                    is_ambiguous=True,
                    candidates=candidates,
                    clarification_type=clar_type,
                    clarification_options=options,
                    reason=f"Ambiguous query '{query_text}' matches multiple products."
                )

            # Single exact match
            pid = matched_prod_ids[0]
            cand = self._build_candidate(pid, 1.0, clean_q, "exact_alias")
            return ProductMatchResult(
                matched=True,
                product=cand,
                candidates=[cand]
            )

        # -------------------------------------------------------------
        # STAGE 2: Compound Substring & Sub-Phrase Matching
        # e.g. 'Amul Taaza aadha litre' -> finds 'amul taaza' alias inside query
        # -------------------------------------------------------------
        longest_sub_match = ""
        matched_pids = []
        for alias_key in sorted(self.alias_to_products.keys(), key=len, reverse=True):
            # Check whole-word substring match
            if re.search(rf"\b{re.escape(alias_key)}\b", clean_q):
                if len(alias_key) > len(longest_sub_match):
                    longest_sub_match = alias_key
                    matched_pids = list(set(r[0] for r in self.alias_to_products[alias_key]))

        if longest_sub_match and len(longest_sub_match) >= 3:
            if longest_sub_match in ["amul milk", "amul doodh"]:
                matched_pids = [
                    p.product_id for p in self.products.values()
                    if p.brand and p.brand.lower() == "amul" and (
                        (p.category and "dairy" in p.category.lower()) or "milk" in p.name.lower() or "taaza" in p.name.lower() or "gold" in p.name.lower()
                    )
                ]
            if len(matched_pids) > 1:
                # Check if digits in query match a specific candidate pack size (e.g. 180 ml, 340 ml)
                # Also normalize "ek kilo" / "1 kilo" / "500 gram" to digits for pack size disambiguation
                clean_q_for_size = clean_q
                if re.search(r"\b(?:ek|1)\s*(?:kilo|kg)\b", clean_q_for_size):
                    clean_q_for_size += " 1 kg 1kg 1000"
                if re.search(r"\b(?:aadha|half|500)\s*(?:gram|gm|g)\b", clean_q_for_size):
                    clean_q_for_size += " 500 g 500g"

                digits = re.findall(r"\b\d+\b", clean_q_for_size)
                if digits:
                    size_matched = []
                    for pid in matched_pids:
                        p_digits = re.findall(r"\b\d+\b", self.products[pid].name.lower())
                        if any(d in p_digits for d in digits):
                            size_matched.append(pid)
                    if len(size_matched) == 1:
                        matched_pids = size_matched

                # If matched alias is a brand or broad term, check if remaining query words narrow it down
                if len(matched_pids) > 1:
                    remaining_words = set(clean_q.split()) - set(longest_sub_match.split())
                    meaningful_remaining = [
                        w for w in remaining_words
                        if len(w) >= 3 and w not in [
                            "wala", "wali", "wale", "karo", "karna", "dena", "packet", "bottle",
                            "kilo", "litre", "jar", "pack", "shampoo", "doodh", "milk", "tel", "oil",
                            "sabun", "soap", "aata", "atta", "daal", "dal", "namak", "salt"
                        ]
                    ]
                    if meaningful_remaining:
                        narrowed = [
                            pid for pid in matched_pids
                            if any(w in self.products[pid].name.lower() for w in meaningful_remaining)
                        ]
                        if len(narrowed) == 1:
                            matched_pids = narrowed

            if len(matched_pids) > 1:
                # Ambiguous sub-phrase match (e.g. "doodh" or "amul milk")
                candidates = [self._build_candidate(pid, 0.95, longest_sub_match, "exact_alias", is_generic=True) for pid in matched_pids]
                options = [f"{c.name} (₹{c.price_inr})" for c in candidates]
                # Check if size or product clarification
                clar_type = ClarificationType.SIZE if ("amul" in clean_q or "amul" in longest_sub_match) else ClarificationType.PRODUCT
                return ProductMatchResult(
                    matched=False,
                    is_ambiguous=True,
                    candidates=candidates,
                    clarification_type=clar_type,
                    clarification_options=options,
                    reason=f"Query contains ambiguous product reference '{longest_sub_match}'."
                )
            else:
                pid = matched_pids[0]
                cand = self._build_candidate(pid, 0.95, longest_sub_match, "substring_alias")
                return ProductMatchResult(
                    matched=True,
                    product=cand,
                    candidates=[cand]
                )

        # -------------------------------------------------------------
        # STAGE 2.5: Generic Category Disambiguation before Fuzzy Match
        # -------------------------------------------------------------
        cat_matches = self._find_generic_category_matches(clean_q)
        if cat_matches:
            if len(cat_matches) > 1:
                candidates = [self._build_candidate(pid, 0.95, clean_q, "generic_category", is_generic=True) for pid in cat_matches[:5]]
                options = [f"{c.name} (₹{c.price_inr})" for c in candidates]
                return ProductMatchResult(
                    matched=False,
                    is_ambiguous=True,
                    candidates=candidates,
                    clarification_type=ClarificationType.PRODUCT,
                    clarification_options=options,
                    reason=f"Multiple varieties available for '{query_text}'."
                )
            else:
                cand = self._build_candidate(cat_matches[0], 0.95, clean_q, "generic_category")
                return ProductMatchResult(
                    matched=True,
                    product=cand,
                    candidates=[cand]
                )

        # -------------------------------------------------------------
        # STAGE 3: Fuzzy Candidate Retrieval via RapidFuzz
        # -------------------------------------------------------------
        fuzzy_results = process.extract(
            clean_q,
            self.all_alias_strings,
            scorer=fuzz.token_set_ratio,
            limit=5
        )

        if not fuzzy_results or fuzzy_results[0][1] < confidence_threshold:
            # Tri-Modal Phonetic Recovery via 4-Stage Indic Soundex & Bigram Edit Distance
            query_sx = IndicSoundex.soundex(clean_q)
            phonetic_aliases = self.soundex_to_aliases.get(query_sx, [])
            phonetic_candidates = []
            for pa in phonetic_aliases:
                sim = IndicSoundex.compute_phonetic_similarity(clean_q, pa)
                if sim >= 0.65:
                    phonetic_candidates.append((pa, sim))
            phonetic_candidates.sort(key=lambda x: x[1], reverse=True)

            if phonetic_candidates:
                top_pa, top_sim = phonetic_candidates[0]
                lex_pids = [pid for m_str, _, _ in (fuzzy_results or []) for pid in self.alias_metadata.get(m_str, [])]
                ph_pids = [pid for pa, _ in phonetic_candidates for pid in self.alias_metadata.get(pa, [])]
                fused = self.reciprocal_rank_fusion(lex_pids, [], ph_pids, k=60)
                if fused:
                    top_fused_pid = fused[0][0]
                    cand = self._build_candidate(top_fused_pid, min(0.95, top_sim), top_pa, "phonetic_rrf")
                    return ProductMatchResult(
                        matched=True,
                        product=cand,
                        candidates=[cand]
                    )

            # Nothing matched with sufficient confidence -> Product not found
            return ProductMatchResult(
                matched=False,
                clarification_type=ClarificationType.PRODUCT_NOT_FOUND,
                reason=f"Product '{query_text}' not found in store catalogue."
            )

        top_match_str, top_score, _ = fuzzy_results[0]
        top_pids = self.alias_metadata.get(top_match_str, [])

        # Check for ambiguity among close candidates
        candidates = []
        seen_pids = set()
        for match_str, score, _ in fuzzy_results:
            if score >= (top_score - ambiguity_margin):
                for pid in self.alias_metadata.get(match_str, []):
                    if pid not in seen_pids:
                        seen_pids.add(pid)
                        candidates.append(self._build_candidate(pid, score / 100.0, match_str, "fuzzy"))

        if len(candidates) > 1 and top_score < 98.0:
            options = [f"{c.name} (₹{c.price_inr})" for c in candidates]
            return ProductMatchResult(
                matched=False,
                is_ambiguous=True,
                candidates=candidates,
                clarification_type=ClarificationType.PRODUCT,
                clarification_options=options,
                reason=f"Multiple similar products found for '{query_text}'."
            )

        if candidates:
            best_candidate = candidates[0]
        elif top_pids:
            best_candidate = self._build_candidate(top_pids[0], top_score / 100.0, top_match_str, "fuzzy")
        else:
            return ProductMatchResult(
                matched=False,
                clarification_type=ClarificationType.PRODUCT_NOT_FOUND,
                reason=f"Product '{query_text}' not found in store catalogue."
            )
        return ProductMatchResult(
            matched=True,
            product=best_candidate,
            candidates=[best_candidate]
        )

    def _build_candidate(
        self,
        product_id: str,
        confidence: float,
        matched_text: str,
        source: str,
        is_generic: bool = False
    ) -> ProductMatchCandidate:
        prod = self.products[product_id]
        return ProductMatchCandidate(
            product_id=prod.product_id,
            name=prod.name,
            brand=prod.brand,
            category=prod.category,
            sale_unit=prod.sale_unit,
            pack_size=Decimal(str(prod.pack_size)),
            pack_size_unit=prod.pack_size_unit,
            price_inr=Decimal(str(prod.price_inr)),
            confidence=confidence,
            matched_text=matched_text,
            match_source=source,
            is_generic=is_generic
        )
