from typing import Literal

from pydantic import BaseModel, Field


class StreamControlMessage(BaseModel):
    type: Literal["start", "analyze", "reset", "end"]
    session_id: str | None = None
    user_id: str | None = None
    audio_format: Literal["wav", "pcm16"] = "wav"
    sample_rate: int | None = Field(default=None, ge=8000, le=48000)


class AntiSpoofStageResult(BaseModel):
    stage: Literal["primary", "secondary"]
    model: str
    spoof_score: float = Field(ge=0, le=1)
    decision: Literal["reject", "challenge", "continue", "genuine"]
    reason: str


class AntiSpoofPipelineResult(BaseModel):
    session_id: str
    user_id: str | None = None
    audio_format: Literal["wav", "pcm16"]
    bytes_processed: int
    final_action: Literal["reject", "challenge", "proceed_biometric"]
    primary: AntiSpoofStageResult
    secondary: AntiSpoofStageResult | None = None
    stt_status: Literal["blocked", "ready_for_handoff"]
    next_step: str
