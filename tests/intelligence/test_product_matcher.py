"""
DukaanSaathi — Test Suite for Product Matching Service (Service 2)
Tests exact alias lookup, canonical names, generic milk ambiguity, RapidFuzz fuzzy retrieval,
and threshold rejection.
"""

import pytest
from backend.app.services.matcher import ProductMatcher
from backend.app.models import Product
from backend.app.schemas.intelligence import ClarificationType

def test_exact_alias_matching(db_session):
    matcher = ProductMatcher(db_session)

    # Test common kirana aliases
    res_aata = matcher.match_product("aata")
    assert res_aata.matched is True
    assert res_aata.product_id == "PRD001"

    res_chini = matcher.match_product("chini")
    assert res_chini.matched is True
    assert res_chini.product_id == "PRD034"

    res_maggi = matcher.match_product("maggi")
    assert res_maggi.matched is True
    assert res_maggi.product_id == "PRD041"

def test_canonical_name_matching(db_session):
    matcher = ProductMatcher(db_session)

    res = matcher.match_product("Loose Wheat Flour (Atta)")
    assert res.matched is True
    assert res.product_id == "PRD001"

    res2 = matcher.match_product("Fortune Sunlite Refined Sunflower Oil 1L")
    assert res2.matched is True
    assert res2.product_id == "PRD032"

def test_generic_milk_ambiguity_never_arbitrary(db_session):
    """
    CRITICAL REQUIREMENT:
    'doodh' alias maps to PRD021 (Amul Taaza), PRD022 (Amul Gold), PRD023 (Mother Dairy).
    The system MUST return is_ambiguous=True and ask the customer to clarify,
    never guessing or arbitrarily selecting a SKU.
    """
    matcher = ProductMatcher(db_session)
    res = matcher.match_product("doodh")

    assert res.matched is False
    assert res.is_ambiguous is True
    assert res.clarification_type == ClarificationType.PRODUCT
    assert len(res.candidates) >= 2
    candidate_ids = {c.product_id for c in res.candidates}
    assert "PRD021" in candidate_ids
    assert "PRD022" in candidate_ids

def test_specific_milk_variant_resolves_cleanly(db_session):
    matcher = ProductMatcher(db_session)

    res_taaza = matcher.match_product("Amul Taaza doodh")
    assert res_taaza.matched is True
    assert res_taaza.product_id == "PRD021"

    res_gold = matcher.match_product("Amul Gold")
    assert res_gold.matched is True
    assert res_gold.product_id == "PRD022"

    res_md = matcher.match_product("Mother Dairy milk")
    assert res_md.matched is True
    assert res_md.product_id == "PRD023"

def test_rapidfuzz_spelling_tolerance(db_session):
    matcher = ProductMatcher(db_session)

    # Phonetic or slightly misspelled query
    res = matcher.match_product("maagi")
    assert res.matched is True
    assert res.product_id == "PRD041"

    res_biscuit = matcher.match_product("Parle-G biskut")
    assert res_biscuit.matched is True
    assert res_biscuit.product_id in ["PRD042", "PRD043"]

def test_unrecognized_product_rejected_without_hallucination(db_session):
    matcher = ProductMatcher(db_session)

    res = matcher.match_product("Dragon Fruit Exotic")
    assert res.matched is False
    assert res.product_id is None
    assert res.is_ambiguous is False

    res_empty = matcher.match_product("")
    assert res_empty.matched is False
    assert res_empty.product_id is None

def test_all_matched_products_exist_in_db(db_session):
    matcher = ProductMatcher(db_session)
    test_queries = ["aata", "chini", "maggi", "amul doodh", "haldi powder", "basmati chawal"]

    for q in test_queries:
        res = matcher.match_product(q)
        if res.matched:
            p = db_session.query(Product).filter(Product.product_id == res.product_id).first()
            assert p is not None, f"Matched product {res.product_id} for query '{q}' does not exist in DB!"
            assert p.is_active is True
