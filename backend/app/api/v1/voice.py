"""
DukaanSaathi — Voice Processing API Router (Phase 4)
Handles audio upload, validation, controlled FFmpeg transcoding, Gnani Prisma STT,
Phase 3 order intelligence, session persistence, assistant text generation,
and Gnani Timbre TTS delivery.
"""

import base64
import logging
import re
import time
import uuid
from typing import Dict, Optional, Tuple
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.core.rate_limiter import enforce_rate_limit
from backend.app.models import OrderSession, Store
from backend.app.schemas.intelligence import IntentType, DialogueState
from backend.app.schemas.voice import (
    VoiceTurnResponse,
    CartSnapshot,
    LatencyBreakdown,
)
from backend.app.services import (
    AudioService,
    AudioValidationError,
    PrismaSTTService,
    TimbreTTSService,
    AssistantResponseGenerator,
    ConversationManager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Pipeline"])

# In-memory turn idempotency cache: (session_id, client_turn_id) -> VoiceTurnResponse
_idempotency_cache: Dict[Tuple[str, str], VoiceTurnResponse] = {}
_MAX_IDEMPOTENCY_ITEMS = 1000


@router.post("/sessions/{session_id}/turn", response_model=VoiceTurnResponse)
async def process_voice_turn(
    session_id: str,
    audio_file: UploadFile = File(..., description="Customer audio recording (WAV, WebM, OGG, MP4, MP3)"),
    store_id: Optional[str] = Form(None),
    customer_id: Optional[str] = Form(None),
    client_turn_id: Optional[str] = Form(None),
    include_audio_base64: bool = Form(False),
    force_mock: bool = Form(False),
    db: Session = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("voice_turn", max_requests=40, window_seconds=60))
):
    """
    Main voice-first turn endpoint:
    Audio Upload -> Preprocessing -> Prisma STT -> Order Intelligence -> Session Persistence -> Response Gen -> Timbre TTS.
    """
    turn_start_time = time.time()

    # 1. Idempotency Check (Task 5)
    if client_turn_id:
        cache_key = (session_id, client_turn_id)
        if cache_key in _idempotency_cache:
            cached = _idempotency_cache[cache_key]
            # Return duplicate response
            dup_resp = cached.model_copy()
            dup_resp.is_duplicate = True
            return dup_resp

    # 2. Receive and Validate Upload
    upload_t0 = time.time()
    try:
        raw_audio_bytes = await audio_file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read audio upload: {e}"
        )
    upload_ms = (time.time() - upload_t0) * 1000

    filename = audio_file.filename or "upload.wav"
    content_type = audio_file.content_type

    # Format & Signature Validation (Task 1)
    try:
        detected_format = AudioService.validate_audio_upload(
            raw_audio_bytes,
            filename=filename,
            content_type=content_type
        )
    except AudioValidationError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )

    # 3. Preprocessing & Inspection (Task 2)
    preproc_t0 = time.time()
    try:
        metadata = AudioService.inspect_audio(raw_audio_bytes, format_hint=detected_format)
        AudioService.validate_duration(metadata)
        pcm_wav_bytes = AudioService.convert_to_pcm16_wav(raw_audio_bytes, original_format=detected_format)
    except AudioValidationError as preproc_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(preproc_err)
        )
    preprocessing_ms = (time.time() - preproc_t0) * 1000

    # 4. Resolve Store and Session (Task 5)
    active_store_id = store_id or settings.DEMO_STORE_ID
    store = db.query(Store).filter(Store.store_id == active_store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store '{active_store_id}' not found"
        )

    sess = db.query(OrderSession).filter(OrderSession.session_id == session_id).first()
    if sess:
        existing_cart = sess.current_cart or []
    else:
        sess = OrderSession(
            session_id=session_id,
            store_id=active_store_id,
            customer_id=customer_id,
            status="active",
            current_cart=[]
        )
        db.add(sess)
        db.flush()
        existing_cart = []

    # 5. Speech-to-Text: Gnani Prisma (Task 3)
    stt_service = PrismaSTTService(force_mock=force_mock)
    stt_res = stt_service.transcribe(pcm_wav_bytes, filename="turn.wav")
    stt_ms = stt_res.latency_ms

    if not stt_res.success:
        # If STT failed with fatal API or network error (Task 9)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Speech recognition service unavailable: {stt_res.error_message}"
        )

    transcript = stt_res.transcript.strip()

    # 6. Order Intelligence Engine (Phase 3 Integration - Task 4)
    intel_t0 = time.time()
    generated_turn_id = client_turn_id or f"turn_{uuid.uuid4().hex[:8]}"

    if not transcript:
        # User spoke nothing or silence
        assistant_text = "Kripya dobara boliye, hum sun nahi paye."
        intent = IntentType.UNKNOWN
        action_name = "prompt_repeat"
        action_details = {"message": assistant_text}
        cart_items = [
            it if isinstance(it, dict) else it.dict()
            for it in existing_cart
        ]
        cart_total = sum(Decimal(str(it.get("subtotal", 0))) for it in cart_items)
        session_state = DialogueState.COLLECTING
        intelligence_ms = (time.time() - intel_t0) * 1000
    else:
        conversation_manager = ConversationManager(db=db, store_id=active_store_id)
        turn_response = conversation_manager.process_turn(
            session_id=session_id,
            user_utterance=transcript,
            existing_cart=existing_cart
        )
        intelligence_ms = (time.time() - intel_t0) * 1000

        # Update Session Cart in DB
        sess.current_cart = [
            {
                "product_id": it.product_id,
                "name": it.name,
                "quantity": float(it.quantity),
                "unit": it.unit,
                "unit_price": float(it.unit_price),
                "subtotal": float(it.subtotal),
                "requested_quantity": float(it.requested_quantity) if it.requested_quantity is not None else None,
                "requested_unit": it.requested_unit
            }
            for it in turn_response.cart
        ]

        if turn_response.state == DialogueState.ORDER_PLACED:
            sess.status = "confirmed"
        elif turn_response.state == DialogueState.CANCELLED:
            sess.status = "expired"

        db.commit()

        # 7. Generate Natural Spoken Response (Task 6)
        assistant_text = AssistantResponseGenerator.generate_response(
            turn_response=turn_response,
            raw_transcript=transcript
        )
        intent = turn_response.intent
        action_name = turn_response.action.action
        action_details = {
            "message": turn_response.action.message,
            "clarification_type": (
                turn_response.action.clarification_type.value
                if turn_response.action.clarification_type else None
            ),
            "clarification_options": turn_response.action.clarification_options,
            "price_quote": float(turn_response.action.price_quote) if turn_response.action.price_quote else None,
            "stock_quote": float(turn_response.action.stock_quote) if turn_response.action.stock_quote else None,
        }
        cart_items = turn_response.cart
        cart_total = turn_response.total_amount
        session_state = turn_response.state

    # 8. Text-to-Speech: Gnani Timbre (Task 7 & 9)
    tts_service = TimbreTTSService(force_mock=force_mock)
    try:
        tts_res = tts_service.synthesize(text=assistant_text)
        tts_ms = tts_res.latency_ms
        audio_status = "generated" if tts_res.success else "failed"
        audio_url = f"/api/v1/voice/audio/{tts_res.audio_id}" if tts_res.success else None
        warning_msg = None if tts_res.success else f"Audio generation unavailable: {tts_res.error_message}"
        audio_b64 = None
        if include_audio_base64 and tts_res.success and tts_res.audio_bytes:
            audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("utf-8")
    except Exception as e:
        logger.warning(f"TTS synthesis failed gracefully: {e}")
        tts_ms = 0.0
        audio_status = "failed"
        audio_url = None
        warning_msg = f"Audio generation unavailable: {e}"
        audio_b64 = None

    total_turn_ms = (time.time() - turn_start_time) * 1000

    # Build Response
    latency_breakdown = LatencyBreakdown(
        upload_ms=round(upload_ms, 2),
        preprocessing_ms=round(preprocessing_ms, 2),
        stt_ms=round(stt_ms, 2),
        intelligence_ms=round(intelligence_ms, 2),
        tts_ms=round(tts_ms, 2),
        total_ms=round(total_turn_ms, 2)
    )

    cart_snapshot = CartSnapshot(
        items=cart_items,
        item_count=len(cart_items),
        total_amount=cart_total
    )

    response_payload = VoiceTurnResponse(
        session_id=session_id,
        turn_id=generated_turn_id,
        transcript=transcript,
        detected_language=stt_res.detected_language,
        intent=intent,
        action=action_name,
        action_details=action_details,
        cart=cart_snapshot,
        assistant_text=assistant_text,
        session_state=session_state,
        audio_status=audio_status,
        audio_url=audio_url,
        audio_base64=audio_b64,
        latency_ms=latency_breakdown,
        is_duplicate=False,
        warning=warning_msg
    )

    # Cache for idempotency
    if client_turn_id:
        if len(_idempotency_cache) >= _MAX_IDEMPOTENCY_ITEMS:
            # Evict first 50 keys
            for k in list(_idempotency_cache.keys())[:50]:
                _idempotency_cache.pop(k, None)
        _idempotency_cache[(session_id, client_turn_id)] = response_payload

    return response_payload


@router.get("/audio/{audio_id}")
def get_synthesized_audio(audio_id: str):
    """
    Serves synthesized WAV audio directly to browser <audio> tags or mobile clients.
    Guards against path traversal or malicious injection in the identifier.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]{4,64}$", audio_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio identifier format. Only alphanumeric, hyphen, and underscore characters are allowed."
        )

    audio_bytes = TimbreTTSService.get_cached_audio(audio_id)
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested audio clip not found or has expired."
        )

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'inline; filename="{audio_id}.wav"',
            "Cache-Control": "public, max-age=3600"
        }
    )
