from typing import Literal

from pydantic import BaseModel, Field


class VoiceControlMessage(BaseModel):
    type: Literal["start", "stop", "ping"]
    session_id: str | None = None
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    language_code: str = "en-US"