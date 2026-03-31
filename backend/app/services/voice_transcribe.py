from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.core.config import Settings


TranscriptCallback = Callable[[str, bool], Awaitable[None]]


class VoicePipelineError(RuntimeError):
    pass


@dataclass(slots=True)
class TranscribeStreamSession:
    stream: object
    handler_task: asyncio.Task[None]

    async def send_audio(self, audio_chunk: bytes) -> None:
        await self.stream.input_stream.send_audio_event(audio_chunk=audio_chunk)

    async def finish(self) -> None:
        await self.stream.input_stream.end_stream()
        await self.handler_task


class AmazonTranscribeStreamingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def start_stream(
        self,
        *,
        sample_rate: int | None,
        language_code: str | None,
        on_transcript: TranscriptCallback,
    ) -> TranscribeStreamSession:
        try:
            from amazon_transcribe.client import TranscribeStreamingClient
            from amazon_transcribe.handlers import TranscriptResultStreamHandler
        except ImportError as exc:
            raise VoicePipelineError(
                "Amazon Transcribe dependencies are not installed. Run the backend requirements install first."
            ) from exc

        media_sample_rate_hz = sample_rate or self._settings.aws_transcribe_sample_rate_hz
        resolved_language_code = language_code or self._settings.aws_transcribe_language_code

        try:
            client = TranscribeStreamingClient(region=self._settings.aws_region)
            stream = await client.start_stream_transcription(
                language_code=resolved_language_code,
                media_sample_rate_hz=media_sample_rate_hz,
                media_encoding=self._settings.aws_transcribe_media_encoding,
            )
        except Exception as exc:
            raise VoicePipelineError(f"Unable to start Amazon Transcribe streaming: {exc}") from exc

        class TranscriptEventHandler(TranscriptResultStreamHandler):
            def __init__(self, output_stream: object, callback: TranscriptCallback) -> None:
                super().__init__(output_stream)
                self._callback = callback

            async def handle_transcript_event(self, transcript_event: object) -> None:
                transcript = getattr(transcript_event, "transcript", None)
                results = getattr(transcript, "results", []) if transcript is not None else []
                for result in results:
                    alternatives = getattr(result, "alternatives", [])
                    if not alternatives:
                        continue
                    transcript_text = getattr(alternatives[0], "transcript", "").strip()
                    if transcript_text:
                        await self._callback(transcript_text, bool(getattr(result, "is_partial", False)))

        handler = TranscriptEventHandler(stream.output_stream, on_transcript)
        return TranscribeStreamSession(stream=stream, handler_task=asyncio.create_task(handler.handle_events()))