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
    "कर दीजिए": "kar do",
    "दीजिए": "de do",
    "कर दो": "kar do",
    "कीजिए": "kar do",
    "खाली कर दो": "khali kar do",
    "खाली कर दीजिए": "khali kar do",
    "खाली करो": "khali kar do",
    "साफ कर दो": "saaf kar do",
    "साफ कर दीजिए": "saaf kar do",
    "साफ करो": "saaf kar do",
    "हटा दो": "hata do",
    "हटा दीजिए": "hata do",
    "निकाल दो": "hata do",
    "निकाल दीजिए": "hata do",
    "कितना हुआ": "kitna hua",
    "कितने पैसे": "kitne paise",
    "कितने रुपए": "kitne rupaye",
    "कितने रुपये": "kitne rupaye",
    "बिल बना दो": "bill bana do",
    "बिल बनाओ": "bill bana do",
    "बिल बनाइए": "bill bana do",
    "बिल तैयार कर दो": "bill bana do",
    "बिल तैयार": "bill bana do",
    "bill बना दो": "bill bana do",
    "bill बनाओ": "bill bana do",
    "bill बना": "bill bana do",
    "bill तैयार कर दो": "bill bana do",
    "bill तैयार": "bill bana do",
    "चेक करो": "check karo",
    "दिखा दो": "dikhao",
    "दिखाइए": "dikhao",
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
    "एक सौ अस्सी": "180",
    "एक सौ पचास": "150",
    "एक सौ": "100",
    "दो सौ": "200",
    "तीन सौ": "300",
    "चार सौ": "400",
    "तीन सौ चालीस": "340",
    "आधा किलो चीनी": "aadha kilo chini",
    "आधा किलो sugar": "aadha kilo chini",
    "আধা কিলো চিনি": "aadha kilo chini",
    # Gujarati numbers & phrases from Prisma
    "એકસો અસ્સી": "180",
    "એક સો અસી": "180",
    "એકસો પચાસ": "150",
    "બસો": "200",
    "ત્રણસો": "300",
    # Gurmukhi numbers & phrases from Prisma
    "ਇੱਕ ਸੌ ਅੱਸੀ": "180",
    "ਇੱਕ ਸੋ ਅੱਸੀ": "180",
    "ਇਕ ਸੌ ਅੱਸੀ": "180",
    "ਇੱਕ ਸੌ ਪੰਜਾਹ": "150",
    "ਦੋ ਸੌ": "200",
    "ਪੰਜ ਸੌ": "500",
    "पारले जी": "parle-g",
    "पारले-जी": "parle-g",
    "एक दो": "2",
    "एक-दो": "2",
    "दो तीन": "2-3",
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
    "ग्यारह": "11", "बारह": "12", "तेरह": "13", "चौदह": "14", "पंद्रह": "15", "सोलह": "16", "सत्रह": "17", "अठारह": "18", "उन्नीस": "19",
    "बीस": "20", "इक्कीस": "21", "बाईस": "22", "तेईस": "23", "चौबीस": "24", "पच्चीस": "25", "छब्बीस": "26", "सत्ताईस": "27", "अट्ठाईस": "28", "उनतीस": "29",
    "तीस": "30", "इकतीस": "31", "बत्तीस": "32", "तैंतीस": "33", "चौंतीस": "34", "पैंतीस": "35", "छत्तीस": "36", "सैंतीस": "37", "अड़तीस": "38", "उनतालीस": "39",
    "चालीस": "40", "पचास": "50", "साठ": "60", "सत्तर": "70", "अस्सी": "80", "नब्बे": "90",
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
    "किसान": "kissan", "किसान-": "kissan", "चिंग्स": "chings", "चिंग्स-": "chings",
    "कैडबरी": "cadbury", "किटकैट": "kitkat", "सेंसोडाइन": "sensodyne", "कोलगेट": "colgate",
    "क्लिनिक": "clinic", "प्लस": "plus", "सनसिल्क": "sunsilk", "पैंटीन": "pantene", "डव": "dove",
    "डेटॉल": "dettol", "लाइफबॉय": "lifebuoy", "हार्पिक": "harpic", "विम": "vim", "सर्फ": "surf",
    "फॉर्च्यून": "fortune", "सफोला": "saffola", "आशीर्वाद": "aashirvaad", "एवरेस्ट": "everest",
    "कैचअप": "ketchup", "केचप": "ketchup", "सॉस": "sauce",
    "बेसन": "besan", "डाबर": "dabur", "आंवला": "amla", "आमला": "amla", "चिप्स": "chips",
    "लेज़": "lays", "लेज": "lays",

    # Conversational & Verbs
    "को": "ko",
    "जगह": "jagah",
    "बदले": "badle",
    "मेरी": "meri", "मेरा": "mera", "मेरे": "mere", "हमारा": "humaara", "हमारी": "humaari",
    "खाली": "khali", "साफ": "saaf", "हटाओ": "hata do", "निकालो": "hata do", "हटा": "hata", "निकाल": "nikal",
    "दिखाओ": "dikhao", "दिखाइए": "dikhao", "दिखाना": "dikhana", "चेक": "check",
    "कुल": "kul", "टोटल": "total", "बिल": "bill", "हिसाब": "hisaab",
    "पैसे": "paise", "रुपए": "rupaye", "रुपये": "rupaye", "रुपया": "rupaye", "रु": "rupaye",
    "कितने": "kitne", "खर्चा": "kharcha",
    "सब": "sab", "सारा": "saara", "सारी": "saari", "सारे": "saare", "पूरा": "poora", "पूरी": "poori",
    "बंद": "band", "शुरू": "shuru", "पता": "pata", "कहाँ": "kahan", "कहां": "kahan", "कब": "kab",
    "समय": "samay", "टाइम": "time", "टाइमिंग": "timing",
    "डिलीवरी": "delivery", "होम": "home", "पेमेंट": "payment", "कैश": "cash",
    "भैया": "bhaiya", "भाई": "bhaiya", "मुझे": "mujhe", "चाहिए": "chahiye", "देना": "dena",
    "और": "aur", "का": "ka", "के": "ke", "की": "ki", "वाला": "wala", "वाली": "wali",
    "कर": "kar", "करो": "kar do", "करिए": "kar do", "दीजिए": "de do",
    "कितना": "kitna", "कितनी": "kitna", "दाम": "daam", "भाव": "daam", "है": "hai", "हैं": "hai",
    "हाँ": "haan", "हां": "haan", "नहीं": "nahi", "नही": "nahi", "पक्का": "confirm",
    "कन्फर्म": "confirm", "कैंसिल": "cancel", "रद्द": "cancel",
    "दोनों": "dono", "दोनो": "dono", "तो": "to", "जो": "jo", "उसका": "uska", "उसके": "uske",
    "काट": "cart", "कार्ट": "cart", "कार्ड": "cart", "कॉर्ड": "cart", "में": "mein", "पे": "pe", "पर": "par",
    "बताना": "batao", "बताओ": "batao", "पड़ा": "pada", "पहले": "pehle", "कुछ": "kuch", "उसमें": "usmein",
    "सेल": "cell", "फिनाइल": "phenyl", "फिनायल": "phenyl", "टिशू": "tissue", "नैपकिन": "napkin",
    "बोला": "bola", "मैंने": "maine", "मैने": "maine",
    "आपके": "aapke", "आपका": "aapka", "आपकी": "aapki", "पास": "paas",
    "तुम्हारे": "tumhare", "तुम्हारा": "tumhara", "तुम्हारी": "tumhari", "तेरे": "tere", "तेरा": "tera", "तेरी": "teri",
    "पत्ती": "patti",
    "दुकान": "dukaan", "दुकानदार": "dukaandaar", "क्या": "kya", "सामान": "samaan",
    "बड़ा": "bada", "बड़ी": "badi", "बड़े": "bade", "छोटा": "chhota",
    "से": "se", "सत्तर": "70", "पचास": "50", "होगी": "hogi", "होगा": "hoga",
    "हो": "ho", "गया": "gaya", "डाल": "daal", "डालो": "daalo",
    "बना": "bana", "बनाओ": "bana", "बनाना": "bana", "बनाइए": "bana",
    "तैयार": "taiyaar", "तैयारी": "taiyaar",
    "भेज": "bhej", "भेजो": "bhejo", "भेजिए": "bhejo",
    "बता": "bata",
    # Bengali common tokens
    "আধা": "aadha", "চিনি": "chini", "কিলো": "kilo", "ডাল": "daal", "দিন": "de do", "দাও": "de do",
    # Gurmukhi common tokens & digits
    "੦": "0", "੧": "1", "੨": "2", "੩": "3", "੪": "4", "੫": "5", "੬": "6", "੭": "7", "੮": "8", "੯": "9",
    "ਇੱਕ": "ek", "ਦੋ": "do", "ਤਿੰਨ": "teen", "ਚਾਰ": "chaar", "ਪੰਜ": "paanch", "ਅੱਧਾ": "aadha", "ਕਿਲੋ": "kilo",
    "ਪੈਕ": "pack", "ਬੋਤਲ": "bottle", "ਨਹੀਂ": "nahi", "ਹੈ": "hai", "ਕਿਆ": "kya", "ਕੀ": "ki",
}

# Common Latin Hinglish spelling mappings to canonical tokens
PHONETIC_SYNONYMS = {
    r"\baata\b": "atta",
    r"\baataa\b": "atta",
    r"\bgehun\b": "gehun",
    r"\bchawal\b": "chawal",
    r"\bcheeni\b": "chini",
    r"\bshakkar\b": "chini",
    r"\bsugar\b": "chini",
    r"\bcatchup\b": "ketchup",
    r"\bcetchup\b": "ketchup",
    r"\bdudh\b": "doodh",
    r"\bnamak\b": "namak",
    r"\bhaldi\b": "haldi",
    r"\bmirch\b": "mirch",
    r"\badha\b": "aadha",
    r"\bpaav\b": "pao",
    r"\bpav\b": "pao",
    r"\bone\s+eighty\b": "180",
    r"\btwo\s+fifty\b": "250",
    r"\bthree\s+forty\b": "340",
    r"\bfive\s+hundred\b": "500",
    r"\baden\s*(?:and|&)?\s*shoulders?\b": "head and shoulders",
    r"\baden\b": "head",
    r"\bhead\s+shoulders\b": "head and shoulders",
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
    r"\bcard\s+(check|dekh|karo|batao|karke|status)\b": "cart \1",
    r"\b(meri|mera|my)\s+card\b": r"\1 cart",
    r"\bcard\s+mein\b": "cart mein",
    r"\bcard\s+khali\b": "cart khali",
    r"\bsale\s+(hoga|hogi|hai|ho\s+gaya)\b": r"cell \1",
}

# Intra-utterance negation / correction triggers (supports both Latin and Devanagari)
CORRECTION_PATTERNS = [
    re.compile(r"^(.*?)(?:\.\.\.|\,)?\s*(?:nahi|नहीं|नही)[,\s]+(.*)$", re.IGNORECASE),
    re.compile(r"^(.*?)\s+(?:nahi|नहीं|नही)\s*,\s*(.*)$", re.IGNORECASE),
    re.compile(r"^(.*?)\s+(?:nahi|नहीं|नही)\s+(.*)$", re.IGNORECASE),
]


class TranscriptNormalizer:
    @staticmethod
    def _clean_indic_subphrase(text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        sub = unicodedata.normalize("NFKC", text).replace("।", " ").strip()
        for dev_phrase, lat_phrase in DEVNAGARI_COMPOUND_PHRASES.items():
            sub = sub.replace(dev_phrase, lat_phrase)
        converted_words = []
        for w in sub.split():
            w_strip = w.strip(".,;:!?\"'")
            if w_strip in DEVNAGARI_TO_LATIN:
                converted_words.append(DEVNAGARI_TO_LATIN[w_strip])
            else:
                converted_words.append(w)
        sub = " ".join(converted_words).lower().strip()
        sub = re.sub(r"[^\w\s\-\.\,\u0900-\u0D7F]", " ", sub)
        for regex_pat, replacement in PHONETIC_SYNONYMS.items():
            sub = re.sub(regex_pat, replacement, sub, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", sub).strip()

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
                # If post is checkout, cart query, cancel, or clarification, this is NOT a quantity correction
                if re.search(r"\b(bill|hisaab|parchi|total|kul|rupaye|paise|confirm|bhejo|bhej|cancel|clear|khali)\b", post, re.IGNORECASE):
                    break
                # If pre was just a conversational filler or repetitive "nahi", this is not a quantity correction
                if re.match(r"^(?:nahi|nahin|नही|नहीं|\s*)+$", pre, re.IGNORECASE):
                    break
                if pre and post:
                    has_correction = True
                    correction_pre = TranscriptNormalizer._clean_indic_subphrase(pre)
                    correction_post = TranscriptNormalizer._clean_indic_subphrase(post)
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

        # 5. Clean punctuation and standardize whitespace (preserving full Indic Unicode blocks)
        clean = clean.lower().strip()
        clean = re.sub(r"[^\w\s\-\.\,\u0900-\u0D7F]", " ", clean)
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

    @staticmethod
    def calculate_devanagari_ratio(text: str) -> float:
        """
        Calculates character-script ratio for Devanagari in bilingual ASR:
        r = |{c in [U+0900..U+097F]}| / non_whitespace_chars
        """
        non_ws = [c for c in text if not c.isspace()]
        if not non_ws:
            return 0.0
        dev_count = sum(1 for c in non_ws if '\u0900' <= c <= '\u097F')
        return round(dev_count / len(non_ws), 4)

    @staticmethod
    def is_hallucinated_noise(raw_text: str) -> bool:
        """
        Enforces Devanagari script ratio filter to catch ungrounded ASR hallucinations:
        Transcripts with r < 0.1 and length > 8 characters of random Latin noise are flagged.
        """
        clean = raw_text.strip()
        if len(clean) <= 8:
            return False
        # If pure Latin text contains common grocery, cart, or conversational words, it is valid Hinglish
        KNOWN_HINGLISH_TOKENS = {
            "atta", "chini", "maggi", "oil", "doodh", "milk", "tea", "chai", "salt", "namak",
            "kilo", "kg", "packet", "pack", "bottle", "litre", "liter", "gm", "gram", "pouch",
            "add", "kar", "do", "de", "chahiye", "dena", "bhaiya", "cart", "total", "bill",
            "namaste", "cancel", "clear", "khali", "ek", "do", "teen", "chaar", "paanch", "aadha"
        }
        tokens = set(re.sub(r"[^\w\s]", " ", clean.lower()).split())
        if tokens.intersection(KNOWN_HINGLISH_TOKENS):
            return False

        r = TranscriptNormalizer.calculate_devanagari_ratio(clean)
        # If no Devanagari and zero known Hinglish/grocery tokens in a long string, flag as potential noise
        return r < 0.1 and len(tokens) >= 3
