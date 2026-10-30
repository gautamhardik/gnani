"""
DukaanSaathi — Transcript Normalization Service (Phase 3 Service 1)
Performs Unicode normalization, punctuation/whitespace cleaning,
intra-utterance correction detection, and colloquial phonetic mappings.
Supports both Hinglish/Latin and Devanagari Hindi transcripts from Gnani Prisma.
"""

import re
import unicodedata
from typing import Tuple, Optional, Dict
from backend.app.schemas.intelligence import NormalizedTranscript

# Devanagari compound phrases to normalize prior to word-level mapping
DEVNAGARI_COMPOUND_PHRASES: Dict[str, str] = {
    "दे दो": "de do",
    "दीजिए": "de do",
    "कर दो": "kar do",
    "कीजिए": "kar do",
    "हटा दो": "hata do",
    "निकाल दो": "hata do",
    "कितने का": "kitne ka",
    "कितने की": "kitne ka",
    "कितने के": "kitne ka",
    "कन्फर्म कर दो": "confirm kar do",
    "पक्का कर दो": "confirm kar do",
    "कैंसिल कर दो": "cancel kar do",
    "रद्द कर दो": "cancel kar do",
    "ढाई सौ": "dhai sau",
    "पाँच सौ": "paanch sau",
    "पांच सौ": "paanch sau",
    "पारले जी": "parle-g",
    "पारले-जी": "parle-g",
    "गुड डे": "good day",
    "तूर दाल": "toor dal",
    "अरहर दाल": "toor dal",
    "मसूर दाल": "masoor dal",
    "टाटा नमक": "tata namak",
}

# Devanagari single-word mapping to standard Latin Hindi tokens
DEVNAGARI_TO_LATIN: Dict[str, str] = {
    # Numerals & Number Words
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4", "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
    "एक": "ek", "दो": "do", "तीन": "teen", "चार": "chaar", "पाँच": "paanch", "पांच": "paanch",
    "छह": "chhe", "छः": "chhe", "छे": "chhe", "सात": "saat", "आठ": "aath", "नौ": "nau", "दस": "das",
    "सौ": "sau", "आधा": "aadha", "पाव": "pao", "पाओ": "pao", "डेढ़": "dedh", "ढाई": "dhai",

    # Units
    "किलो": "kilo", "किग्रा": "kilo", "केजी": "kilo", "केज़ी": "kilo", "ग्राम": "gram", "ग्रा": "gram",
    "लीटर": "litre", "मिली": "ml", "मिलीलीटर": "ml", "पैकेट": "packet", "पैक": "packet",
    "जार": "jar", "बोतल": "bottle", "पीस": "piece", "डब्बा": "box",

    # Groceries & Brands
    "आटा": "atta", "आता": "atta", "गेहूँ": "gehun", "गेहूं": "gehun", "चावल": "chawal",
    "चीनी": "chini", "शक्कर": "chini", "मैगी": "maggi", "दूध": "doodh", "अमूल": "amul",
    "ताजा": "taaza", "ताज़ा": "taaza", "गोल्ड": "gold", "पारले": "parle-g",
    "दाल": "dal", "तूर": "toor", "अरहर": "toor", "मसूर": "masoor", "नमक": "namak",
    "टाटा": "tata", "तेल": "oil", "सरसों": "mustard", "घी": "ghee", "चाय": "chai", "कॉफी": "coffee",
    "नेस्कैफे": "nescafe", "बिस्कुट": "biscuit", "बिस्किट": "biscuit", "कोक": "coke",
    "बेसन": "besan", "डाबर": "dabur", "आंवला": "amla", "आमला": "amla", "चिप्स": "chips",
    "लेज़": "lays", "लेज": "lays",

    # Conversational & Verbs
    "भैया": "bhaiya", "भाई": "bhaiya", "मुझे": "mujhe", "चाहिए": "chahiye", "देना": "dena",
    "और": "aur", "का": "ka", "के": "ke", "की": "ki", "वाला": "wala", "वाली": "wali",
    "कितना": "kitna", "कितनी": "kitna", "दाम": "daam", "भाव": "daam", "है": "hai", "हैं": "hai",
    "हाँ": "haan", "हां": "haan", "नहीं": "nahi", "नही": "nahi", "पक्का": "confirm",
    "कन्फर्म": "confirm", "कैंसिल": "cancel", "रद्द": "cancel",
}

# Common Latin Hinglish spelling mappings to canonical tokens
PHONETIC_SYNONYMS = {
    r"\baata\b": "atta",
    r"\baataa\b": "atta",
    r"\bgehun\b": "gehun",
    r"\bchawal\b": "chawal",
    r"\bcheeni\b": "chini",
    r"\bshakkar\b": "chini",
    r"\bdudh\b": "doodh",
    r"\bnamak\b": "namak",
    r"\bhaldi\b": "haldi",
    r"\bmirch\b": "mirch",
    r"\badha\b": "aadha",
    r"\bpaav\b": "pao",
    r"\bpav\b": "pao",
    r"\bkg\b": "kilo",
    r"\bkgs\b": "kilo",
    r"\bgm\b": "gram",
    r"\bgms\b": "gram",
    r"\bltr\b": "litre",
    r"\bpkt\b": "packet",
    r"\bpkts\b": "packet",
    r"\bpouches\b": "pouch",
    r"\bbottles\b": "bottle",
    r"\bjars\b": "jar",
}

# Intra-utterance negation / correction triggers (supports both Latin and Devanagari)
CORRECTION_PATTERNS = [
    re.compile(r"^(.*?)(?:\.\.\.|\,)?\s*(?:nahi|नहीं|नही)[,\s]+(.*)$", re.IGNORECASE),
    re.compile(r"^(.*?)\s+(?:nahi|नहीं|नही)\s*,\s*(.*)$", re.IGNORECASE),
    re.compile(r"^(.*?)\s+(?:nahi|नहीं|नही)\s+(.*)$", re.IGNORECASE),
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

        # Replace Hindi full stop Danda (।) with space
        normalized = normalized.replace("।", " ")

        # 2. Check for intra-utterance correction: e.g. "Ek kilo chini... nahi, aadha kilo kar do"
        has_correction = False
        correction_pre = None
        correction_post = None

        for pattern in CORRECTION_PATTERNS:
            match = pattern.match(normalized.strip())
            if match:
                pre = match.group(1).strip()
                post = match.group(2).strip()
                if pre and post:
                    has_correction = True
                    correction_pre = pre
                    correction_post = post
                    break

        clean = normalized.strip()

        # 3. Apply Devanagari compound phrase normalization
        for dev_phrase, lat_phrase in DEVNAGARI_COMPOUND_PHRASES.items():
            clean = clean.replace(dev_phrase, lat_phrase)

        # 4. Word-by-word Devanagari to Latin standardization
        words = clean.split()
        converted_words = []
        for w in words:
            w_strip = w.strip(".,;:!?\"'")
            if w_strip in DEVNAGARI_TO_LATIN:
                converted_words.append(DEVNAGARI_TO_LATIN[w_strip])
            else:
                converted_words.append(w)
        clean = " ".join(converted_words)

        # 5. Clean punctuation and standardize whitespace
        clean = clean.lower().strip()
        clean = re.sub(r"[^\w\s\-\.\,]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        # 6. Apply Latin phonetic synonyms
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
