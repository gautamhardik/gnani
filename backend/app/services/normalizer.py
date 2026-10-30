"""
DukaanSaathi — Transcript Normalization Service (Phase 3 Service 1)
Performs Unicode normalization, punctuation/whitespace cleaning,
intra-utterance correction detection, and colloquial phonetic mappings.
"""

import re
import unicodedata
from typing import Tuple, Optional
from backend.app.schemas.intelligence import NormalizedTranscript

# Common Hindi/Hinglish spelling mappings to canonical tokens
PHONETIC_SYNONYMS = {
    # Flours & Grains
    r"\baata\b": "atta",
    r"\baataa\b": "atta",
    r"\bgehun\b": "gehun",
    r"\bchawal\b": "chawal",
    # Sugar & Sweeteners
    r"\bcheeni\b": "chini",
    r"\bshakkar\b": "chini",
    # Dairy
    r"\bdudh\b": "doodh",
    # Salt & Spices
    r"\bnamak\b": "namak",
    r"\bhaldi\b": "haldi",
    r"\bmirch\b": "mirch",
    # Numbers & Units
    r"\badha\b": "aadha",
    r"\badha\b": "aadha",
    r"\bpaav\b": "pao",
    r"\bpav\b": "pao",
    r"\bkg\b": "kilo",
    r"\bkgs\b": "kilo",
    r"\bgm\b": "gram",
    r"\bgms\b": "gram",
    r"\bltr\b": "litre",
    r"\bltr\b": "litre",
    r"\bpkt\b": "packet",
    r"\bpkts\b": "packet",
    r"\bpouches\b": "pouch",
    r"\bbottles\b": "bottle",
    r"\bjars\b": "jar",
}

# Intra-utterance negation / correction triggers
CORRECTION_PATTERNS = [
    re.compile(r"^(.*?)(?:\.\.\.|\,)?\s*nahi[,\s]+(.*)$", re.IGNORECASE),
    re.compile(r"^(.*?)\s+nahi\s*,\s*(.*)$", re.IGNORECASE),
    re.compile(r"^(.*?)\s+nahi\s+(.*)$", re.IGNORECASE),
]

class TranscriptNormalizer:
    @staticmethod
    def normalize(raw_text: str) -> NormalizedTranscript:
        if not raw_text:
            return NormalizedTranscript(
                raw_transcript="",
                clean_text="",
                tokens=[],
                has_correction=False
            )

        # 1. Unicode Normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", raw_text)

        # 2. Check for intra-utterance correction: e.g. "Ek kilo chini... nahi, aadha kilo kar do"
        has_correction = False
        correction_pre = None
        correction_post = None

        for pattern in CORRECTION_PATTERNS:
            match = pattern.match(normalized.strip())
            if match:
                pre = match.group(1).strip()
                post = match.group(2).strip()
                # Ensure post is non-empty and has substance
                if pre and post:
                    has_correction = True
                    correction_pre = pre
                    correction_post = post
                    break

        # 3. Clean and standardize whitespace and punctuation
        clean = normalized.lower().strip()

        # Preserve hyphens in brand names like Parle-G
        clean = re.sub(r"[^\w\s\-\.\,]", " ", clean)
        # Collapse multiple spaces
        clean = re.sub(r"\s+", " ", clean).strip()

        # 4. Apply phonetic spelling standardization
        for regex_pat, replacement in PHONETIC_SYNONYMS.items():
            clean = re.sub(regex_pat, replacement, clean, flags=re.IGNORECASE)

        clean = re.sub(r"\s+", " ", clean).strip()
        tokens = [t.strip(".,") for t in clean.split() if t.strip(".,")]

        return NormalizedTranscript(
            raw_transcript=raw_text,
            clean_text=clean,
            tokens=tokens,
            has_correction=has_correction,
            correction_pre=correction_pre,
            correction_post=correction_post
        )
