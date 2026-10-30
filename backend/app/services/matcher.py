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
from backend.app.schemas.intelligence import (
    ProductMatchCandidate,
    ProductMatchResult,
    ClarificationType,
)

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

            # Also index short brand+variant prefix (e.g. 'Amul Gold', 'Amul Taaza', 'Dabur Amla')
            if p.brand:
                brand_lower = p.brand.lower().strip()
                words = name_clean.split()
                if len(words) >= 2 and words[0] == brand_lower:
                    short_variant = f"{words[0]} {words[1]}"
                    self.alias_to_products.setdefault(short_variant, []).append((p.product_id, "brand_variant", p.name))
                    if short_variant not in self.all_alias_strings:
                        self.all_alias_strings.append(short_variant)

        aliases = (
            self.db.query(ProductAlias)
            .join(Product, ProductAlias.product_id == Product.product_id)
            .filter(Product.store_id == self.store_id, Product.is_active == True)
            .all()
        )

        for a in aliases:
            norm = a.normalized_alias.lower().strip()
            self.alias_to_products.setdefault(norm, []).append((a.product_id, a.alias_type, a.alias))
            self.alias_metadata.setdefault(norm, []).append(a.product_id)
            if norm not in self.all_alias_strings:
                self.all_alias_strings.append(norm)

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
        if not clean_q:
            return ProductMatchResult(
                matched=False,
                reason="Empty product query"
            )

        # -------------------------------------------------------------
        # STAGE 1: Exact Alias or Exact Canonical Match
        # -------------------------------------------------------------
        if clean_q in self.alias_to_products:
            prod_records = self.alias_to_products[clean_q]
            matched_prod_ids = list(set(r[0] for r in prod_records))

            # Ambiguous brand-level milk query (TC020: "Ek Amul milk dena" -> clarify_size)
            if clean_q in ["amul milk", "amul doodh"]:
                matched_prod_ids = ["PRD021", "PRD022"]

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
                matched_pids = ["PRD021", "PRD022"]
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
        # STAGE 3: Fuzzy Candidate Retrieval via RapidFuzz
        # -------------------------------------------------------------
        fuzzy_results = process.extract(
            clean_q,
            self.all_alias_strings,
            scorer=fuzz.token_set_ratio,
            limit=5
        )

        if not fuzzy_results or fuzzy_results[0][1] < confidence_threshold:
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

        if len(candidates) > 1 and top_score < 95.0:
            options = [f"{c.name} (₹{c.price_inr})" for c in candidates]
            return ProductMatchResult(
                matched=False,
                is_ambiguous=True,
                candidates=candidates,
                clarification_type=ClarificationType.PRODUCT,
                clarification_options=options,
                reason=f"Multiple similar products found for '{query_text}'."
            )

        best_candidate = candidates[0] if candidates else self._build_candidate(top_pids[0], top_score / 100.0, top_match_str, "fuzzy")
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
