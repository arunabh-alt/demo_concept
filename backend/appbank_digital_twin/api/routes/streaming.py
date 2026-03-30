from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from appbank_digital_twin.core.config import get_settings
from appbank_digital_twin.schemas.streaming import StreamControlMessage
from appbank_digital_twin.services.anti_spoof import SequentialAntiSpoofService
from appbank_digital_twin.services.streaming_session import VoiceStreamingSession


router = APIRouter(tags=["streaming"])
settings = get_settings()
anti_spoof_service = SequentialAntiSpoofService(settings)


@router.websocket("/stt/ws")
async def stt_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    session: VoiceStreamingSession | None = None

    await websocket.send_json(
        {
            "type": "ready",
            "message": "Send a start control message, then binary audio chunks, then an analyze control message.",
            "supported_audio_formats": ["wav", "pcm16"],
        }
    )

    try:
        while True:
            message = await websocket.receive()

            if message.get("bytes") is not None:
                if session is None:
                    await websocket.send_json({"type": "error", "message": "Start a session before sending audio."})
                    continue

                try:
                    session.append_audio(message["bytes"], max_bytes=settings.streaming_max_audio_bytes)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue

                await websocket.send_json(
                    {
                        "type": "audio_received",
                        "session_id": session.session_id,
                        "bytes_received": session.bytes_received,
                    }
                )
                continue

            if message.get("text") is not None:
                try:
                    payload = StreamControlMessage.model_validate(json.loads(message["text"]))
                except (json.JSONDecodeError, ValidationError) as exc:
                    await websocket.send_json({"type": "error", "message": f"Invalid control message: {exc}"})
                    continue

                if payload.type == "start":
                    session = VoiceStreamingSession(
                        session_id=payload.session_id or VoiceStreamingSession().session_id,
                        user_id=payload.user_id,
                        audio_format=payload.audio_format,
                        sample_rate=payload.sample_rate,
                    )
                    await websocket.send_json(
                        {
                            "type": "session_started",
                            "session_id": session.session_id,
                            "audio_format": session.audio_format,
                            "sample_rate": session.sample_rate,
                        }
                    )
                    continue

                if session is None:
                    await websocket.send_json({"type": "error", "message": "No active session. Send a start message first."})
                    continue

                if payload.type == "reset":
                    session.reset()
                    await websocket.send_json({"type": "session_reset", "session_id": session.session_id})
                    continue

                if payload.type == "end":
                    await websocket.send_json({"type": "session_ended", "session_id": session.session_id})
                    return

                if payload.type == "analyze":
                    try:
                        result = anti_spoof_service.evaluate(session)
                    except ValueError as exc:
                        await websocket.send_json({"type": "error", "message": str(exc)})
                        continue

                    await websocket.send_json(
                        {
                            "type": "anti_spoof_result",
                            **result.model_dump(),
                        }
                    )
                    continue

    except WebSocketDisconnect:
        return