"""
DukaanSaathi — Streaming Text-to-Speech & Bilingual Semantic Chunking Service
Implements the O(1) regex boundary heuristic (checkFlush), emoji sanitization,
and asynchronous first-in-first-stream chunking for sub-second Voice-to-Voice TTFA.
"""

import re
import asyncio
import base64
import logging
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Any

from backend.app.services.text_to_speech import TimbreTTSService, TTSResult

logger = logging.getLogger(__name__)

# Curated abbreviation blocklist to prevent premature mid-clause flushing
ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "rs.", "inr", "kg.", "gm.", "g.", "pkt.", "pkts.",
    "ltr.", "ml.", "approx.", "etc.", "i.e.", "e.g.", "no.", "vs.", "sq."
}

# Regex to strip non-lexical emojis and trailing Unicode symbols that cause synthesis spikes
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def sanitize_tts_text(text: str) -> str:
    """
    Strips trailing non-lexical Unicode tokens and emojis before TTS synthesis,
    preventing severe Real-Time Factor (RTF) spikes.
    """
    clean = EMOJI_PATTERN.sub("", text)
    # Remove excess whitespace
    clean = re.sub(r"[ \t]+", " ", clean).strip()
    return clean


def check_flush(buffer: str) -> bool:
    """
    Deterministic O(1) regex boundary heuristic to identify semantic clause endpoints.
    Evaluates three trigger classes in strict priority order:
      1. Indic and native morphology (Devanagari danda । or ॥)
      2. Latin terminal punctuation (., ?, !) guarded by abbreviation blocklist
      3. Structural clause delimiters (\n, —, ...)

    Enforces minimum clause constraint of 30 characters and hard ceiling of 220 characters.
    """
    if len(buffer) < 30:
        return False
    if len(buffer) >= 220:
        return True

    # Priority 1: Indic Danda Hard Sentence Boundary (Devanagari । or ॥)
    if re.search(r"[।॥]", buffer):
        return True

    # Priority 2: Latin Terminal Punctuation (. ? !) guarded by abbreviation blocklist
    match = re.search(r"(\b\w+[\.\?!])\s*$", buffer)
    if match:
        token = match.group(1).lower()
        if token not in ABBREVIATIONS:
            return True

    # Priority 3: Structural Delimiters (\n, —, ...)
    if re.search(r"(\n|—|\.\.\.)", buffer):
        return True

    return False


class StreamingTTSWorker:
    """
    First-In-First-Stream (ttsQueue) worker that dispatches semantic clauses to
    the TTS engine while text is still generating, achieving sub-second Time-to-First-Audio.
    """

    def __init__(self, tts_service: Optional[TimbreTTSService] = None):
        self.tts_service = tts_service or TimbreTTSService()

    def segment_text_into_clauses(self, full_text: str) -> List[str]:
        """
        Splits full response text into optimal semantic clauses respecting check_flush rules.
        """
        sanitized = sanitize_tts_text(full_text)
        if not sanitized:
            return []

        clauses: List[str] = []
        current_buf = ""

        # Tokenize by words with spaces
        tokens = re.split(r"(\s+)", sanitized)
        for token in tokens:
            current_buf += token
            if check_flush(current_buf):
                clause = current_buf.strip()
                if clause:
                    clauses.append(clause)
                current_buf = ""

        if current_buf.strip():
            # If remaining trailing buffer is small and we already have clauses, merge with last
            trailing = current_buf.strip()
            if clauses and len(trailing) < 20:
                clauses[-1] = f"{clauses[-1]} {trailing}"
            else:
                clauses.append(trailing)

        return clauses

    async def stream_synthesized_chunks(
        self,
        text_stream: AsyncGenerator[str, None],
        language: str = "hi"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Consumes an async generator of text tokens, dynamically chunks into semantic clauses
        using check_flush, synthesizes audio chunks concurrently, and yields synthesized payloads.
        """
        buffer = ""
        chunk_index = 0

        async for token in text_stream:
            buffer += token
            if check_flush(buffer):
                clause = sanitize_tts_text(buffer)
                buffer = ""
                if clause:
                    res: TTSResult = await asyncio.to_thread(
                        self.tts_service.synthesize,
                        text=clause,
                        language=language
                    )
                    b64 = base64.b64encode(res.audio_bytes).decode("utf-8") if res.audio_bytes else None
                    yield {
                        "chunk_index": chunk_index,
                        "text": clause,
                        "audio_base64": b64,
                        "audio_id": res.audio_id,
                        "latency_ms": res.latency_ms,
                        "is_final": False,
                    }
                    chunk_index += 1

        # Flush remaining buffer
        if buffer.strip():
            clause = sanitize_tts_text(buffer)
            if clause:
                res: TTSResult = await asyncio.to_thread(
                    self.tts_service.synthesize,
                    text=clause,
                    language=language
                )
                b64 = base64.b64encode(res.audio_bytes).decode("utf-8") if res.audio_bytes else None
                yield {
                    "chunk_index": chunk_index,
                    "text": clause,
                    "audio_base64": b64,
                    "audio_id": res.audio_id,
                    "latency_ms": res.latency_ms,
                    "is_final": True,
                }
