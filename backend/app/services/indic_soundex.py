"""
DukaanSaathi — Indic Soundex & Phonetic Retrieval Service
Implements the 4-stage Indic Soundex phonetic encoding algorithm and bigram edit-distance
matching tailored for code-mixed Indian kirana commerce, brand names, and ASR phonetic errors.
"""

import re
from typing import Tuple, List, Optional
from rapidfuzz import fuzz


class IndicSoundex:
    """
    4-Stage Indic Soundex encoder:
    Stage 1: Retroflex Normalization (Tamil retroflex zh -> l)
    Stage 2: Character Normalization (w->v, q->k, f->ph, x->ks)
    Stage 3: Phoneme & Vowel Compression (Aspirates, clusters, geminates, long vowels)
    Stage 4: Articulation Encoding (Place of articulation digits)
    """

    @classmethod
    def normalize_stage1_retroflex(cls, text: str) -> str:
        s = text.lower()
        s = s.replace("azha", "ala").replace("izhi", "ili").replace("uzhu", "ulu")
        s = s.replace("zh", "l")
        return s

    @classmethod
    def normalize_stage2_characters(cls, text: str) -> str:
        s = text
        s = re.sub(r"ksh", "__KSH__", s)
        s = s.replace("w", "v").replace("q", "k").replace("f", "ph").replace("x", "ks")
        s = s.replace("__KSH__", "ksh")
        return s

    @classmethod
    def normalize_stage3_compression(cls, text: str) -> str:
        s = text
        # Aspirated Digraphs
        s = (
            s.replace("bh", "B")
            .replace("ch", "C")
            .replace("dh", "D")
            .replace("gh", "G")
            .replace("jh", "J")
            .replace("kh", "K")
            .replace("ph", "P")
            .replace("th", "T")
            .replace("sh", "S")
        )
        # Compound Clusters
        s = s.replace("ksh", "X").replace("gy", "G").replace("ny", "N").replace("ng", "N")
        # Geminates / Double consonants
        s = re.sub(r"([b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z])\1+", r"\1", s)
        # Long Vowels & Diphthongs
        s = (
            s.replace("aa", "a")
            .replace("ee", "i")
            .replace("oo", "u")
            .replace("ai", "e")
            .replace("au", "o")
        )
        return s

    @classmethod
    def encode_stage4_articulation(cls, text: str, extended: bool = False) -> str:
        if not text:
            return "0000"

        first_char = text[0].upper()
        remainder = text[1:]

        code_map = {
            # Vowels & Semivowels
            "a": "0", "e": "0", "i": "0", "o": "0", "u": "0", "y": "0", "h": "0",
            # Labials
            "b": "1", "p": "1", "m": "1", "v": "1", "B": "1", "P": "1",
            # Velars
            "k": "2", "g": "2", "c": "2", "K": "2", "G": "2", "X": "2",
            # Dentals
            "d": "3", "t": "3", "D": "3", "T": "3",
            # Palatals & Fricatives
            "j": "4", "z": "4", "s": "4", "C": "4", "J": "4", "S": "4",
            # Nasals
            "n": "5", "N": "5",
            # Liquids / Glides
            "l": "6", "r": "6",
        }

        digits: List[str] = []
        prev_digit = code_map.get(text[0].lower(), "")

        for char in remainder:
            digit = code_map.get(char, code_map.get(char.lower(), "7"))
            if digit != "0" and digit != prev_digit:
                digits.append(digit)
            prev_digit = digit

        res = first_char + "".join(digits)
        # Pad or truncate to 4 characters
        return (res + "0000")[:4]

    @classmethod
    def soundex(cls, text: str) -> str:
        """Computes the 4-stage Indic Soundex code for a word."""
        clean = re.sub(r"[^\w]", "", text.strip())
        if not clean:
            return "0000"
        s1 = cls.normalize_stage1_retroflex(clean)
        s2 = cls.normalize_stage2_characters(s1)
        s3 = cls.normalize_stage3_compression(s2)
        return cls.encode_stage4_articulation(s3)

    @classmethod
    def compute_phonetic_similarity(cls, word1: str, word2: str) -> float:
        """
        Calculates hybrid phonetic and edit similarity score in [0.0, 1.0].
        Combines exact Indic Soundex match + Token Set Ratio + Levenshtein.
        """
        w1_clean = re.sub(r"[^\w]", "", word1.lower())
        w2_clean = re.sub(r"[^\w]", "", word2.lower())
        if not w1_clean or not w2_clean:
            return 0.0

        if w1_clean == w2_clean:
            return 1.0

        sx1 = cls.soundex(w1_clean)
        sx2 = cls.soundex(w2_clean)

        soundex_match = 1.0 if sx1 == sx2 else 0.0
        fuzz_ratio = fuzz.ratio(w1_clean, w2_clean) / 100.0
        token_ratio = fuzz.token_set_ratio(w1_clean, w2_clean) / 100.0

        # Weighted combination favoring phonetic match
        combined = (0.5 * soundex_match) + (0.3 * token_ratio) + (0.2 * fuzz_ratio)
        return round(combined, 4)
