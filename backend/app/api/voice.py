from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import resolve_user_from_token
from app.schemas.voice import VoiceControlMessage
from app.services.voice_transcribe import AmazonTranscribeStreamingService, TranscribeStreamSession, VoicePipelineError


router = APIRouter(prefix="/voice", tags=["voice"])
settings = get_settings()
transcribe_service = AmazonTranscribeStreamingService(settings)


@router.websocket("/pipeline/ws")
async def voice_pipeline(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    db = SessionLocal()
    user = resolve_user_from_token(token, db)
    if user is None:
        await websocket.close(code=4401, reason="Invalid token")
        db.close()
        return

    await websocket.accept()
    session_id = f"voice_{uuid4().hex[:12]}"
    stream_session: TranscribeStreamSession | None = None
    transcript_parts: list[str] = []

    await websocket.send_json(
        {
            "type": "ready",
            "session_id": session_id,
            "user_id": str(user.id),
            "message": "Send a start message, then PCM16 mono audio bytes, then stop.",
        }
    )

    async def on_transcript(transcript_text: str, is_partial: bool) -> None:
        if not is_partial:
            transcript_parts.append(transcript_text)
        await websocket.send_json(
            {
                "type": "transcript",
                "session_id": session_id,
                "is_partial": is_partial,
                "text": transcript_text,
            }
        )

    try:
        while True:
            message = await websocket.receive()

            if message.get("bytes") is not None:
                if stream_session is None:
                    await websocket.send_json({"type": "error", "message": "Start the stream before sending audio."})
                    continue

                await stream_session.send_audio(message["bytes"])
                continue

            if message.get("text") is None:
                continue

            try:
                payload = VoiceControlMessage.model_validate(json.loads(message["text"]))
            except (json.JSONDecodeError, ValidationError) as exc:
                await websocket.send_json({"type": "error", "message": f"Invalid control message: {exc}"})
                continue

            if payload.type == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
                continue

            if payload.type == "start":
                if stream_session is not None:
                    await websocket.send_json({"type": "error", "message": "A stream is already active."})
                    continue

                transcript_parts.clear()
                session_id = payload.session_id or f"voice_{uuid4().hex[:12]}"
                try:
                    stream_session = await transcribe_service.start_stream(
                        sample_rate=payload.sample_rate,
                        language_code=payload.language_code,
                        on_transcript=on_transcript,
                    )
                except VoicePipelineError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue

                await websocket.send_json(
                    {
                        "type": "session_started",
                        "session_id": session_id,
                        "sample_rate": payload.sample_rate,
                        "language_code": payload.language_code,
                    }
                )
                continue

            if payload.type == "stop":
                if stream_session is None:
                    await websocket.send_json({"type": "error", "message": "No active stream to stop."})
                    continue

                await stream_session.finish()
                stream_session = None

                transcript = " ".join(part.strip() for part in transcript_parts if part.strip()).strip()
                if not transcript:
                    await websocket.send_json({"type": "error", "message": "No transcript returned from Amazon Transcribe."})
                    continue

                await websocket.send_json(
                    {
                        "type": "transcript_complete",
                        "session_id": session_id,
                        "transcript": transcript,
                    }
                )
                continue

    except WebSocketDisconnect:
        if stream_session is not None:
            try:
                await stream_session.finish()
            except Exception:
                pass
    finally:
        db.close()