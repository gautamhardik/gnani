"""
Unit tests for Streaming TTS Worker and Bilingual Semantic checkFlush Heuristics.
"""

import pytest
import asyncio
from backend.app.services.streaming_tts import (
    check_flush,
    sanitize_tts_text,
    StreamingTTSWorker,
    ABBREVIATIONS,
)


def test_sanitize_tts_text_strips_emojis_and_normalizes_spaces():
    raw = "Namaste bhaiya! 🙏 Aapko kya chahiye? 🛒✨   "
    clean = sanitize_tts_text(raw)
    assert "🙏" not in clean
    assert "🛒" not in clean
    assert "✨" not in clean
    assert clean == "Namaste bhaiya! Aapko kya chahiye?"


def test_check_flush_minimum_length_constraint():
    # Less than 30 characters should not flush even with punctuation
    short_buf = "Haan ji."
    assert len(short_buf) < 30
    assert check_flush(short_buf) is False


def test_check_flush_indic_danda_priority():
    # Buffer >= 30 chars with Devanagari danda ।
    indic_buf = "नमस्ते भैया! आप कैसे हैं। आज क्या लेंगे?"
    assert len(indic_buf) >= 30
    assert check_flush(indic_buf) is True


def test_check_flush_latin_terminal_punctuation_and_abbreviations():
    # Buffer ending with abbreviation like 'rs.' or 'kg.' should NOT flush
    abbrev_buf = "Aapka total bill ban gaya hai Rs."
    assert len(abbrev_buf) >= 30
    assert check_flush(abbrev_buf) is False

    # Valid sentence ending with period
    sentence_buf = "Aapka order humne taiyaar kar diya hai."
    assert len(sentence_buf) >= 30
    assert check_flush(sentence_buf) is True


def test_check_flush_structural_delimiters():
    # Delimiter with newline or ellipsis
    newline_buf = "Dukaan mein toor dal aur chawal uplabdh hain.\n"
    assert len(newline_buf) >= 30
    assert check_flush(newline_buf) is True

    ellipsis_buf = "Ek minute rukiye bhaiya, check kar raha hoon..."
    assert len(ellipsis_buf) >= 30
    assert check_flush(ellipsis_buf) is True


def test_check_flush_hard_maximum_cap():
    # Long text >= 220 chars forces flush to prevent run-on latency
    long_buf = "A" * 225
    assert check_flush(long_buf) is True


@pytest.mark.asyncio
async def test_streaming_tts_worker_segmentation():
    worker = StreamingTTSWorker()
    full_text = (
        "Namaste bhaiya! Sharma Kirana Store mein aapka swagat hai. "
        "Aapki cart mein humne 1 kilo Tata Salt add kar diya hai. "
        "Aur kuch chahiye bhaiya?"
    )
    clauses = worker.segment_text_into_clauses(full_text)
    assert len(clauses) >= 2
    assert all(len(c) > 0 for c in clauses)
    # Check that reconstructed text covers all words
    joined = " ".join(clauses)
    assert "Tata Salt" in joined
    assert "Sharma Kirana Store" in joined

