"""
DukaanSaathi — Voice Processing API Router (Phase 4)
Handles audio upload, validation, controlled FFmpeg transcoding, Gnani Prisma STT,
Phase 3 order intelligence, session persistence, assistant text generation,
and Gnani Timbre TTS delivery.
"""

import asyncio
import base64
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from decimal import Decimal

from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.core.rate_limiter import enforce_rate_limit
from backend.app.models import OrderSession, Store, Order, OrderItem, Product
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
from backend.app.services.llm_service import LLMKiranaService
from backend.app.services.streaming_tts import StreamingTTSWorker, check_flush, sanitize_tts_text
from backend.app.services.normalizer import TranscriptNormalizer
from backend.app.services.intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Pipeline"])

# In-memory turn idempotency cache with thread safety: (session_id, client_turn_id) -> VoiceTurnResponse
_idempotency_cache: Dict[Tuple[str, str], VoiceTurnResponse] = {}
_idempotency_lock = threading.Lock()
_MAX_IDEMPOTENCY_ITEMS = 1000

# Contextual filler phrase bank mapping intent -> immediate acknowledgment (<150 ms)
INTENT_FILLER_BANK = {
    IntentType.STOCK_QUERY: "Ek minute bhaiya, dukaan ka stock check karta hoon.",
    IntentType.CATALOG_QUERY: "Dukaan mein kya-kya samaan hai, abhi batata hoon.",
    IntentType.PRICE_QUERY: "Ji bhaiya, abhi rate dekh ke batata hoon.",
    IntentType.ADD: "Haan bhaiya, abhi pack karta hoon.",
    IntentType.CART_QUERY: "Aapki cart check kar raha hoon bhaiya.",
    IntentType.VIEW_CART: "Aapki cart check kar raha hoon bhaiya.",
    IntentType.CONFIRM: "Aapka hisaab jod raha hoon bhaiya.",
}


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
        with _idempotency_lock:
            cached = _idempotency_cache.get(cache_key)
        if cached:
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

    # 3. Preprocessing & Inspection (Task 2) - Non-blocking threadpool execution
    preproc_t0 = time.time()
    try:
        metadata = await run_in_threadpool(AudioService.inspect_audio, raw_audio_bytes, detected_format)
        AudioService.validate_duration(metadata)
        pcm_wav_bytes = await run_in_threadpool(AudioService.convert_to_pcm16_wav, raw_audio_bytes, detected_format)
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

    # 5. Speech-to-Text: Gnani Prisma (Task 3) - Non-blocking threadpool execution
    stt_service = PrismaSTTService(force_mock=force_mock)
    stt_res = await run_in_threadpool(stt_service.transcribe, pcm_wav_bytes, "turn.wav")
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
        transcript = ""
        table_data = None
        table_title = None
        assistant_text = "(Khali awaz / Silence)"
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
        created_order_id = None
        created_order_dict = None
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

        created_order_id = None
        created_order_dict = None

        if turn_response.state == DialogueState.ORDER_PLACED and turn_response.cart:
            # Check if order already exists for this session
            existing_order = db.query(Order).filter(Order.session_id == session_id).first()
            if not existing_order:
                new_order_id = f"ORD{uuid.uuid4().hex[:8].upper()}"
                order_total = Decimal("0.00")
                items_to_add = []
                for it in turn_response.cart:
                    prod = db.query(Product).filter(
                        Product.product_id == it.product_id,
                        Product.store_id == active_store_id
                    ).first()
                    unit_price = prod.price_inr if prod else it.unit_price
                    subtotal = unit_price * it.quantity
                    order_total += subtotal
                    order_item = OrderItem(
                        item_id=f"ITM{uuid.uuid4().hex[:8].upper()}",
                        order_id=new_order_id,
                        product_id=it.product_id,
                        product_name_snapshot=prod.name if prod else it.name,
                        quantity=it.quantity,
                        unit=prod.sale_unit if prod else it.unit,
                        unit_price=unit_price,
                        subtotal=subtotal
                    )
                    items_to_add.append(order_item)

                new_order = Order(
                    order_id=new_order_id,
                    store_id=active_store_id,
                    session_id=session_id,
                    customer_id=sess.customer_id,
                    total_amount=order_total,
                    status="pending"
                )
                db.add(new_order)
                db.flush()
                for item in items_to_add:
                    db.add(item)
                sess.status = "confirmed"
                db.commit()
                db.refresh(new_order)
                created_order_id = new_order.order_id
                created_order_dict = {
                    "order_id": new_order.order_id,
                    "store_id": new_order.store_id,
                    "session_id": new_order.session_id,
                    "customer_id": new_order.customer_id,
                    "total_amount": float(new_order.total_amount),
                    "status": new_order.status,
                    "created_at": new_order.created_at.isoformat() if new_order.created_at else None,
                    "items": [
                        {
                            "item_id": itm.item_id,
                            "order_id": itm.order_id,
                            "product_id": itm.product_id,
                            "product_name_snapshot": itm.product_name_snapshot,
                            "quantity": float(itm.quantity),
                            "unit": itm.unit,
                            "unit_price": float(itm.unit_price),
                            "subtotal": float(itm.subtotal)
                        }
                        for itm in items_to_add
                    ]
                }
            else:
                created_order_id = existing_order.order_id
                created_order_dict = {
                    "order_id": existing_order.order_id,
                    "store_id": existing_order.store_id,
                    "session_id": existing_order.session_id,
                    "customer_id": existing_order.customer_id,
                    "total_amount": float(existing_order.total_amount),
                    "status": existing_order.status,
                    "created_at": existing_order.created_at.isoformat() if existing_order.created_at else None,
                    "items": [
                        {
                            "item_id": itm.item_id,
                            "order_id": itm.order_id,
                            "product_id": itm.product_id,
                            "product_name_snapshot": itm.product_name_snapshot,
                            "quantity": float(itm.quantity),
                            "unit": itm.unit,
                            "unit_price": float(itm.unit_price),
                            "subtotal": float(itm.subtotal)
                        }
                        for itm in existing_order.items
                    ]
                }
                sess.status = "confirmed"
                db.commit()
        elif turn_response.state == DialogueState.CANCELLED:
            sess.status = "expired"
            db.commit()
        else:
            db.commit()

        # 7. Generate Conversational Response with LLM & Live Inventory Grounding
        deterministic_resp = AssistantResponseGenerator.generate_response(
            turn_response=turn_response,
            raw_transcript=transcript
        )

        llm_service = LLMKiranaService(db=db, store_id=active_store_id)
        cart_dicts = [
            it.dict() if hasattr(it, "dict") else it for it in turn_response.cart
        ]
        
        # Invoke LLM for natural dialogue or inventory tables
        llm_spoken, table_data, table_title = llm_service.generate_reply(
            user_utterance=transcript,
            cart_items=cart_dicts,
            cart_total=turn_response.total_amount,
            deterministic_action_hint=deterministic_resp
        )
        assistant_text = llm_spoken or deterministic_resp
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

    # 8. Text-to-Speech: Gnani Timbre (Task 7 & 9) - Non-blocking threadpool execution
    if not transcript:
        # Don't synthesize audio or speak out loud for ambient silence
        tts_ms = 0.0
        audio_status = "skipped_silence"
        audio_url = None
        warning_msg = None
        audio_b64 = None
    else:
        tts_service = TimbreTTSService(force_mock=force_mock)
        try:
            tts_res = await run_in_threadpool(tts_service.synthesize, text=assistant_text)
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

    # Record turn in persistent session conversation history in DB
    history_entry = {
        "turn_id": generated_turn_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transcript": transcript,
        "assistant_text": assistant_text,
        "intent": intent.value if hasattr(intent, "value") else str(intent),
        "action": action_name,
        "cart": [
            {
                "product_id": it.product_id if hasattr(it, "product_id") else it.get("product_id"),
                "name": it.name if hasattr(it, "name") else it.get("name"),
                "quantity": float(it.quantity if hasattr(it, "quantity") else it.get("quantity", 0)),
                "unit": it.unit if hasattr(it, "unit") else it.get("unit"),
                "unit_price": float(it.unit_price if hasattr(it, "unit_price") else it.get("unit_price", 0)),
                "subtotal": float(it.subtotal if hasattr(it, "subtotal") else it.get("subtotal", 0)),
            }
            for it in cart_items
        ],
        "total_amount": float(cart_total),
        "session_state": session_state.value if hasattr(session_state, "value") else str(session_state),
        "audio_url": audio_url,
    }
    history_list = list(sess.conversation_history or [])
    if transcript and transcript.strip():
        history_list.append(history_entry)
        sess.conversation_history = history_list
        db.commit()

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
        table_data=table_data,
        table_title=table_title,
        latency_ms=latency_breakdown,
        is_duplicate=False,
        warning=warning_msg,
        order_id=created_order_id,
        order=created_order_dict,
        conversation_history=history_list
    )

    # Cache for idempotency with thread lock
    if client_turn_id:
        with _idempotency_lock:
            if len(_idempotency_cache) >= _MAX_IDEMPOTENCY_ITEMS:
                # Evict first 50 keys
                for k in list(_idempotency_cache.keys())[:50]:
                    _idempotency_cache.pop(k, None)
            _idempotency_cache[(session_id, client_turn_id)] = response_payload

    return response_payload


@router.get("/greeting")
async def get_agent_greeting():
    """
    Synthesizes introductory welcome greeting for hands-free conversational call.
    """
    greeting_text = "Namaste bhaiya! Everyday Needs General Store mein aapka swagat hai. Aaj aapko kya-kya chahiye?"
    tts_service = TimbreTTSService()
    try:
        tts_res = await run_in_threadpool(tts_service.synthesize, text=greeting_text)
        audio_url = f"/api/v1/voice/audio/{tts_res.audio_id}" if tts_res.success else None
    except Exception as e:
        logger.warning(f"Greeting TTS failed: {e}")
        audio_url = None
        
    return {
        "text": greeting_text,
        "audio_url": audio_url,
        "success": True
    }


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


@router.websocket("/sessions/{session_id}/stream")
async def voice_streaming_endpoint(websocket: WebSocket, session_id: str):
    """
    Full-duplex WebSocket stream for sub-second agentic voice commerce:
    Supports streaming audio chunks, instant filler phrases (<150 ms),
    bilingual semantic TTS chunking (checkFlush), and sub-millisecond barge-in.
    """
    await websocket.accept()
    logger.info(f"WebSocket voice stream connected for session {session_id}")
    tts_worker = StreamingTTSWorker()
    tts_service = TimbreTTSService()
    stt_service = PrismaSTTService()
    normalizer = TranscriptNormalizer()
    classifier = IntentClassifier()

    # Active turn abort flag for sub-millisecond barge-in
    abort_event = asyncio.Event()

    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")

            if msg_type == "barge_in":
                # Sub-millisecond barge-in trigger: abort active TTS streaming
                abort_event.set()
                await websocket.send_json({
                    "type": "barge_in_ack",
                    "timestamp": time.time(),
                    "message": "Playback stream aborted for barge-in"
                })
                continue

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
                continue

            if msg_type in ["text_query", "audio_turn"]:
                abort_event.clear()
                turn_t0 = time.time()
                store_id = msg.get("store_id", "STORE001")
                raw_text = msg.get("text", "")

                # If audio was uploaded over websocket as base64
                if msg_type == "audio_turn" and "audio_base64" in msg:
                    audio_bytes = base64.b64decode(msg["audio_base64"])
                    stt_res = await run_in_threadpool(stt_service.transcribe, audio_bytes=audio_bytes)
                    raw_text = stt_res.transcript or ""

                if not raw_text.strip():
                    await websocket.send_json({
                        "type": "turn_error",
                        "error": "Empty utterance received",
                        "text": "Kripya dobara boliye, hum sun nahi paye."
                    })
                    continue

                # Check for ASR hallucinated noise
                if normalizer.is_hallucinated_noise(raw_text):
                    await websocket.send_json({
                        "type": "stt_mishear",
                        "raw_transcript": raw_text,
                        "text": "Bhaiya aawaz saaf nahi aayi, kripya dobara boliye."
                    })
                    continue

                # Rapid intent classification for filler phrase selection
                norm_res = normalizer.normalize(raw_text)
                predicted_intent, _ = classifier.classify_intent(
                    norm_res.clean_text,
                    has_intra_correction=norm_res.has_correction
                )

                # Send contextual filler phrase within <150 ms to mask DB / LLM latency
                filler_text = INTENT_FILLER_BANK.get(predicted_intent)
                if filler_text:
                    await websocket.send_json({
                        "type": "filler",
                        "text": filler_text,
                        "intent": predicted_intent.value
                    })

                # Process turn through database and ConversationManager
                db = next(get_db())
                try:
                    conv_mgr = ConversationManager(db, store_id=store_id)
                    turn_resp = conv_mgr.process_turn(session_id=session_id, user_utterance=raw_text)

                    # Generate natural Kirana assistant response text
                    assistant_text = AssistantResponseGenerator.generate_response(
                        turn_response=turn_resp,
                        raw_transcript=raw_text
                    )

                    # Segment into semantic clauses and stream audio chunks
                    clauses = tts_worker.segment_text_into_clauses(assistant_text)
                    for i, clause in enumerate(clauses):
                        if abort_event.is_set():
                            logger.info(f"Session {session_id}: Stream chunk {i} aborted by user barge-in.")
                            break

                        tts_res = await run_in_threadpool(tts_service.synthesize, text=clause, language="hi")
                        audio_b64 = (
                            base64.b64encode(tts_res.audio_bytes).decode("utf-8")
                            if (tts_res.success and tts_res.audio_bytes)
                            else None
                        )
                        await websocket.send_json({
                            "type": "audio_chunk",
                            "chunk_index": i,
                            "total_chunks": len(clauses),
                            "text": clause,
                            "audio_base64": audio_b64,
                            "audio_id": tts_res.audio_id,
                            "is_final": (i == len(clauses) - 1)
                        })

                    # Send final turn completion payload
                    cart_payload = [
                        {
                            "product_id": it.product_id,
                            "name": it.name,
                            "quantity": float(it.quantity),
                            "unit": it.unit,
                            "unit_price": float(it.unit_price),
                            "subtotal": float(it.subtotal),
                        }
                        for it in turn_resp.cart
                    ]
                    await websocket.send_json({
                        "type": "turn_complete",
                        "session_id": session_id,
                        "text": assistant_text,
                        "intent": turn_resp.intent.value,
                        "state": turn_resp.state.value,
                        "cart": cart_payload,
                        "total_amount": float(turn_resp.total_amount),
                        "turn_latency_ms": round((time.time() - turn_t0) * 1000, 2)
                    })
                finally:
                    db.close()

    except WebSocketDisconnect:
        logger.info(f"WebSocket stream disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
