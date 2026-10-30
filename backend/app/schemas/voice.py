"""
DukaanSaathi — Voice API Schemas (Phase 4)
Defines data structures for audio ingestion, turn responses, latency tracking,
and assistant voice outputs.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from backend.app.schemas.intelligence import CartItem, IntentType, DialogueState


class LatencyBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upload_ms: float = Field(default=0.0, description="Time taken to receive and read audio payload")
    preprocessing_ms: float = Field(default=0.0, description="Time taken for validation and FFmpeg conversion")
    stt_ms: float = Field(default=0.0, description="Time taken for Prisma speech-to-text transcription")
    intelligence_ms: float = Field(default=0.0, description="Time taken for Phase 3 order intelligence engine")
    tts_ms: float = Field(default=0.0, description="Time taken for Timbre text-to-speech synthesis")
    total_ms: float = Field(default=0.0, description="Total end-to-end turn processing latency")


class CartSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[CartItem] = Field(default_factory=list)
    item_count: int = Field(default=0)
    total_amount: Decimal = Field(default=Decimal("0.00"))


class VoiceTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    turn_id: str
    transcript: str
    detected_language: str = "hi-IN"
    intent: IntentType
    action: str
    action_details: Dict[str, Any] = Field(default_factory=dict)
    cart: CartSnapshot
    assistant_text: str
    session_state: DialogueState
    audio_status: str = Field(
        ...,
        description="'generated' when TTS succeeds, 'failed' when TTS fails, 'cached' when reused, 'skipped' when not requested"
    )
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    latency_ms: LatencyBreakdown
    is_duplicate: bool = False
    warning: Optional[str] = None


class AudioMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    format: str
    duration_seconds: float
    sample_rate: int
    channels: int
    bit_depth: Optional[int] = None
    file_size_bytes: int

