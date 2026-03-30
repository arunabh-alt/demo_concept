from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class VoiceStreamingSession:
    user_id: str | None = None
    audio_format: str = "wav"
    sample_rate: int | None = None
    session_id: str = field(default_factory=lambda: f"stream_{uuid4().hex[:12]}")
    _audio_buffer: bytearray = field(default_factory=bytearray)

    def append_audio(self, chunk: bytes, max_bytes: int) -> None:
        new_size = len(self._audio_buffer) + len(chunk)
        if new_size > max_bytes:
            raise ValueError(f"Audio buffer limit exceeded: {new_size} bytes > {max_bytes} bytes")
        self._audio_buffer.extend(chunk)

    def reset(self) -> None:
        self._audio_buffer.clear()

    @property
    def bytes_received(self) -> int:
        return len(self._audio_buffer)

    def snapshot(self) -> bytes:
        return bytes(self._audio_buffer)
