"""
DukaanSaathi — Phase 8 Speech Recognition (ASR) Evaluation Engine
Workstream 3: WER & Named Entity Preservation Evaluation across 30 Cases

Measures:
- Verbatim Word Error Rate (WER) using Levenshtein distance on tokens
- Normalized Word Error Rate (using TranscriptNormalizer)
- Named Entity Preservation:
  - Product SKUs & Canonical terms
  - Brand Names (Amul, Maggi, Parle-G, Nescafe, Tata, Good Day, Dabur, Coke)
  - Numerical Quantities & Colloquial Number words
  - Commercial Units (kilo, packet, litre, gram, jar, bottle)
- Denominators, exact counts, match percentages, and failure instances
- Disaggregated breakdown by Language (Hindi, Hinglish, English) and Acoustic Condition (WAV vs WebM)
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.normalizer import TranscriptNormalizer

PERF_TRIALS_PATH = ROOT / "data" / "benchmarks" / "phase_8_performance_trials.json"
VOICE_CASES_PATH = ROOT / "data" / "data" / "voice_test_cases.json"
OUTPUT_PATH = ROOT / "data" / "benchmarks" / "phase_8_speech_evaluation.json"


def levenshtein_tokens(ref: List[str], hyp: List[str]) -> Tuple[int, int, int, int]:
    """Computes substitutions, deletions, insertions, and reference word count."""
    r_len, h_len = len(ref), len(hyp)
    dp = [[0] * (h_len + 1) for _ in range(r_len + 1)]

    for i in range(r_len + 1):
        dp[i][0] = i
    for j in range(h_len + 1):
        dp[0][j] = j

    for i in range(1, r_len + 1):
        for j in range(1, h_len + 1):
            if ref[i - 1].lower() == hyp[j - 1].lower():
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],       # Deletion
                    dp[i][j - 1],       # Insertion
                    dp[i - 1][j - 1]    # Substitution
                )

    total_edits = dp[r_len][h_len]
    return total_edits, r_len


def tokenize_clean(text: str) -> List[str]:
    # Strip punctuation and whitespace
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in clean.split() if t]


# Recognizable entity lexicons for grocery evaluation
BRANDS = {"amul", "maggi", "parle-g", "parle", "nescafe", "tata", "good day", "goodday", "coke", "dabur", "lays", "taaza", "gold"}
UNITS = {"kilo", "kg", "gram", "gm", "g", "packet", "pouch", "litre", "liter", "l", "ml", "bottle", "jar", "pao"}
QUANTITY_WORDS = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "250", "500", "ek", "do", "teen", "char", "paanch", "chhe", "saat", "aath", "nau", "das", "aadha", "half", "quarter", "one", "two", "three"}
PRODUCT_TERMS = {"aata", "atta", "chini", "cheeni", "sugar", "doodh", "milk", "biscuit", "noodles", "chawal", "rice", "dal", "toor", "masoor", "namak", "salt", "besan", "coffee", "ghee", "tel", "oil", "chips"}


def evaluate_speech():
    with open(PERF_TRIALS_PATH, "r", encoding="utf-8") as f:
        perf_data = json.load(f)

    with open(VOICE_CASES_PATH, "r", encoding="utf-8") as f:
        cases_meta = {c["case_id"]: c for c in json.load(f)}

    normalizer = TranscriptNormalizer()
    trials = perf_data.get("trials", [])

    total_ref_words = 0
    total_verbatim_edits = 0
    total_norm_ref_words = 0
    total_norm_edits = 0

    # Entity counters
    entity_metrics = {
        "brands": {"total": 0, "preserved": 0, "failures": []},
        "units": {"total": 0, "preserved": 0, "failures": []},
        "quantities": {"total": 0, "preserved": 0, "failures": []},
        "products": {"total": 0, "preserved": 0, "failures": []}
    }

    # Breakdown by condition and language
    breakdown_cond = {
        "wav": {"ref_words": 0, "edits": 0, "cases": 0},
        "webm": {"ref_words": 0, "edits": 0, "cases": 0}
    }
    breakdown_lang = {
        "hi-Latn": {"ref_words": 0, "edits": 0, "cases": 0},
        "en": {"ref_words": 0, "edits": 0, "cases": 0},
        "code-mix": {"ref_words": 0, "edits": 0, "cases": 0}
    }

    case_evals: List[Dict[str, Any]] = []

    for trial in trials:
        if not trial.get("success"):
            continue

        case_id = trial["case_id"]
        meta = cases_meta.get(case_id, {})
        lang = meta.get("language", "hi-Latn")
        lang_group = "code-mix" if "code" in meta.get("category", "") or "mix" in meta.get("category", "") else ("en" if lang == "en" else "hi-Latn")
        fmt = trial.get("format", "wav")

        ref_text = trial["spoken_input"]
        hyp_text = trial["transcript"]

        ref_tokens = tokenize_clean(ref_text)
        hyp_tokens = tokenize_clean(hyp_text)

        edits, n_ref = levenshtein_tokens(ref_tokens, hyp_tokens)
        total_verbatim_edits += edits
        total_ref_words += n_ref

        # Normalized WER
        norm_ref = normalizer.normalize(ref_text).clean_text
        norm_hyp = normalizer.normalize(hyp_text).clean_text
        norm_ref_toks = norm_ref.split()
        norm_hyp_toks = norm_hyp.split()

        norm_edits, n_norm_ref = levenshtein_tokens(norm_ref_toks, norm_hyp_toks)
        total_norm_edits += norm_edits
        total_norm_ref_words += n_norm_ref

        # Breakdowns
        breakdown_cond[fmt]["ref_words"] += n_norm_ref
        breakdown_cond[fmt]["edits"] += norm_edits
        breakdown_cond[fmt]["cases"] += 1

        if lang_group not in breakdown_lang:
            breakdown_lang[lang_group] = {"ref_words": 0, "edits": 0, "cases": 0}
        breakdown_lang[lang_group]["ref_words"] += n_norm_ref
        breakdown_lang[lang_group]["edits"] += norm_edits
        breakdown_lang[lang_group]["cases"] += 1

        # Check entity preservation
        hyp_text_lower = hyp_text.lower()
        ref_text_lower = ref_text.lower()

        # 1. Brands
        for b in BRANDS:
            if b in ref_text_lower:
                entity_metrics["brands"]["total"] += 1
                if b in hyp_text_lower:
                    entity_metrics["brands"]["preserved"] += 1
                else:
                    entity_metrics["brands"]["failures"].append({"case_id": case_id, "entity": b, "ref": ref_text, "hyp": hyp_text})

        # 2. Units
        for u in UNITS:
            if re.search(r"\b" + re.escape(u) + r"\b", ref_text_lower):
                entity_metrics["units"]["total"] += 1
                if re.search(r"\b" + re.escape(u) + r"\b", hyp_text_lower):
                    entity_metrics["units"]["preserved"] += 1
                else:
                    entity_metrics["units"]["failures"].append({"case_id": case_id, "entity": u, "ref": ref_text, "hyp": hyp_text})

        # 3. Quantities
        for q in QUANTITY_WORDS:
            if re.search(r"\b" + re.escape(q) + r"\b", ref_text_lower):
                entity_metrics["quantities"]["total"] += 1
                if re.search(r"\b" + re.escape(q) + r"\b", hyp_text_lower):
                    entity_metrics["quantities"]["preserved"] += 1
                else:
                    entity_metrics["quantities"]["failures"].append({"case_id": case_id, "entity": q, "ref": ref_text, "hyp": hyp_text})

        # 4. Products
        for p in PRODUCT_TERMS:
            if re.search(r"\b" + re.escape(p) + r"\b", ref_text_lower):
                entity_metrics["products"]["total"] += 1
                if re.search(r"\b" + re.escape(p) + r"\b", hyp_text_lower):
                    entity_metrics["products"]["preserved"] += 1
                else:
                    entity_metrics["products"]["failures"].append({"case_id": case_id, "entity": p, "ref": ref_text, "hyp": hyp_text})

        case_evals.append({
            "case_id": case_id,
            "format": fmt,
            "language_group": lang_group,
            "reference_text": ref_text,
            "raw_transcript": hyp_text,
            "normalized_reference": norm_ref,
            "normalized_transcript": norm_hyp,
            "verbatim_edits": edits,
            "normalized_edits": norm_edits,
            "ref_word_count": n_ref
        })

    # Calculate percentages
    verbatim_wer = (total_verbatim_edits / max(1, total_ref_words)) * 100
    norm_wer = (total_norm_edits / max(1, total_norm_ref_words)) * 100

    def get_pct(ent_key):
        t = entity_metrics[ent_key]["total"]
        p = entity_metrics[ent_key]["preserved"]
        return round((p / t) * 100 if t > 0 else 100.0, 2)

    brand_preservation_pct = get_pct("brands")
    unit_preservation_pct = get_pct("units")
    qty_preservation_pct = get_pct("quantities")
    prod_preservation_pct = get_pct("products")

    cond_wer = {}
    for c, data in breakdown_cond.items():
        cond_wer[c] = {
            "cases": data["cases"],
            "wer_pct": round((data["edits"] / max(1, data["ref_words"])) * 100, 2)
        }

    lang_wer = {}
    for l, data in breakdown_lang.items():
        lang_wer[l] = {
            "cases": data["cases"],
            "wer_pct": round((data["edits"] / max(1, data["ref_words"])) * 100, 2)
        }

    report = {
        "timestamp": perf_data.get("timestamp"),
        "total_cases_evaluated": len(case_evals),
        "total_reference_tokens": total_ref_words,
        "metrics": {
            "verbatim_wer_pct": round(verbatim_wer, 2),
            "normalized_wer_pct": round(norm_wer, 2),
            "accuracy_normalized_pct": round(100.0 - norm_wer, 2)
        },
        "named_entity_preservation": {
            "brands": {
                "total": entity_metrics["brands"]["total"],
                "preserved": entity_metrics["brands"]["preserved"],
                "accuracy_pct": brand_preservation_pct,
                "failures_count": len(entity_metrics["brands"]["failures"])
            },
            "units": {
                "total": entity_metrics["units"]["total"],
                "preserved": entity_metrics["units"]["preserved"],
                "accuracy_pct": unit_preservation_pct,
                "failures_count": len(entity_metrics["units"]["failures"])
            },
            "quantities": {
                "total": entity_metrics["quantities"]["total"],
                "preserved": entity_metrics["quantities"]["preserved"],
                "accuracy_pct": qty_preservation_pct,
                "failures_count": len(entity_metrics["quantities"]["failures"])
            },
            "product_terms": {
                "total": entity_metrics["products"]["total"],
                "preserved": entity_metrics["products"]["preserved"],
                "accuracy_pct": prod_preservation_pct,
                "failures_count": len(entity_metrics["products"]["failures"])
            }
        },
        "breakdowns": {
            "by_condition": cond_wer,
            "by_language": lang_wer
        },
        "failures_sample": {
            "brand_failures": entity_metrics["brands"]["failures"][:5],
            "unit_failures": entity_metrics["units"]["failures"][:5]
        },
        "case_evaluations": case_evals
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print("PHASE 8 SPEECH RECOGNITION (ASR) EVALUATION REPORT")
    print(f"Total Utterances:            {len(case_evals)} / 30")
    print(f"Total Reference Tokens:      {total_ref_words}")
    print(f"Verbatim WER:                {verbatim_wer:.2f}%")
    print(f"Normalized WER:              {norm_wer:.2f}% (Accuracy: {100.0 - norm_wer:.2f}%)")
    print(f"Brand Name Preservation:     {brand_preservation_pct}% ({entity_metrics['brands']['preserved']}/{entity_metrics['brands']['total']})")
    print(f"Unit Preservation:           {unit_preservation_pct}% ({entity_metrics['units']['preserved']}/{entity_metrics['units']['total']})")
    print(f"Quantity Preservation:       {qty_preservation_pct}% ({entity_metrics['quantities']['preserved']}/{entity_metrics['quantities']['total']})")
    print(f"Product Term Preservation:   {prod_preservation_pct}% ({entity_metrics['products']['preserved']}/{entity_metrics['products']['total']})")
    print("Condition Breakdown:")
    for c, d in cond_wer.items():
        print(f"  - {c.upper()}: {d['wer_pct']}% WER ({d['cases']} cases)")
    print("Language Breakdown:")
    for l, d in lang_wer.items():
        print(f"  - {l}: {d['wer_pct']}% WER ({d['cases']} cases)")
    print(f"Saved speech evaluation payload to: {OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    evaluate_speech()
