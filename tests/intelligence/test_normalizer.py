import pytest
from backend.app.services.normalizer import TranscriptNormalizer

def test_unicode_and_whitespace_normalization():
    raw = "  Mujhe   ek\xa0kilo  aata  chahiye...  "
    norm = TranscriptNormalizer.normalize(raw)
    assert norm.raw_transcript == raw
    assert "atta" in norm.clean_text
    assert "aata" not in norm.clean_text
    assert norm.tokens[0] == "mujhe"

def test_phonetic_synonyms():
    # cheeni -> chini
    norm1 = TranscriptNormalizer.normalize("Do kilo cheeni aur shakkar dena")
    assert "chini" in norm1.clean_text
    assert "cheeni" not in norm1.clean_text

    # dudh -> doodh
    norm2 = TranscriptNormalizer.normalize("Ek litre dudh dena")
    assert "doodh" in norm2.clean_text

def test_intra_utterance_correction_detection():
    # TC017 pattern
    raw = "Ek kilo chini... nahi, aadha kilo kar do."
    norm = TranscriptNormalizer.normalize(raw)
    assert norm.has_correction is True
    assert "chini" in norm.correction_pre.lower()
    assert "aadha kilo" in norm.correction_post.lower()

    # Simple sentence without correction
    raw2 = "Bhaiya ek kilo chini aur do packet Maggi dena."
    norm2 = TranscriptNormalizer.normalize(raw2)
    assert norm2.has_correction is False

