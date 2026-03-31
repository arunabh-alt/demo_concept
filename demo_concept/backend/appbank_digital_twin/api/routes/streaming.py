from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from appbank_digital_twin.core.config import get_settings
from appbank_digital_twin.schemas.streaming import PipelineCompletion, StreamControlMessage
from appbank_digital_twin.services.action_router import ActionRouterService, MockActionService
from appbank_digital_twin.services.intent_detection import IntentDetectionService
from appbank_digital_twin.services.transcribe_stream import AmazonTranscribeStreamingService, TranscribeStreamSession


router = APIRouter(tags=["pipeline"])
settings = get_settings()
transcribe_service = AmazonTranscribeStreamingService(settings)
intent_detection_service = IntentDetectionService(settings)
mock_action_service = MockActionService()
action_router_service = ActionRouterService(mock_action_service)


@router.websocket("/pipeline/ws")
async def voice_pipeline(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = f"stream_{uuid4().hex[:12]}"
    stream_session: TranscribeStreamSession | None = None
    transcript_parts: list[str] = []

    await websocket.send_json(
        {
            "type": "ready",
            "message": "Send a start control message, stream PCM16 mono audio bytes, then send stop.",
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
                    await websocket.send_json({"type": "error", "message": "Start the session before sending audio."})
                    continue

                await stream_session.send_audio(message["bytes"])
                if settings.pipeline_chunk_acknowledgements:
                    await websocket.send_json({"type": "audio_received", "session_id": session_id})
                continue

            if message.get("text") is None:
                continue

            try:
                payload = StreamControlMessage.model_validate(json.loads(message["text"]))
            except (json.JSONDecodeError, ValidationError) as exc:
                await websocket.send_json({"type": "error", "message": f"Invalid control message: {exc}"})
                continue

            if payload.type == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
                continue

            if payload.type == "start":
                if stream_session is not None:
                    await websocket.send_json({"type": "error", "message": "A stream is already active for this socket."})
                    continue

                session_id = payload.session_id or f"stream_{uuid4().hex[:12]}"
                transcript_parts.clear()
                stream_session = await transcribe_service.start_stream(
                    sample_rate=payload.sample_rate,
                    language_code=payload.language_code or settings.aws_transcribe_language_code,
                    on_transcript=on_transcript,
                )
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

                intent = await intent_detection_service.detect_intent(transcript)
                await websocket.send_json({"type": "intent", "session_id": session_id, **intent.model_dump()})

                action_result = await action_router_service.route(transcript, intent)
                completion = PipelineCompletion(
                    session_id=session_id,
                    transcript=transcript,
                    intent=intent,
                    action_result=action_result,
                )
                await websocket.send_json({"type": "pipeline_complete", **completion.model_dump()})
                continue

    except WebSocketDisconnect:
        if stream_session is not None:
            try:
                await stream_session.finish()
            except Exception:
                return