from typing import Any, Literal

from pydantic import BaseModel, Field


class StreamControlMessage(BaseModel):
    type: Literal["start", "stop", "ping"]
    session_id: str | None = None
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    language_code: str = "en-US"


class IntentResult(BaseModel):
    intent: str
    action: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    slots: dict[str, Any] = Field(default_factory=dict)
    provider: str


class MockActionRequest(BaseModel):
    action: str
    transcript: str = Field(min_length=1)
    intent: str
    slots: dict[str, Any] = Field(default_factory=dict)


class MockActionResponse(BaseModel):
    action: str
    endpoint: str
    status: Literal["mocked", "completed"]
    payload: dict[str, Any]


class PipelineCompletion(BaseModel):
    session_id: str
    transcript: str
    intent: IntentResult
    action_result: MockActionResponse
