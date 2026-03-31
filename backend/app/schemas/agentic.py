from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentExecutionRequest(BaseModel):
    user_id: UUID
    agent_id: UUID
    message: str = Field(min_length=1, max_length=1000)


class AgentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    role: str
    mode_preference: str
    description: str | None = None
    is_primary: bool
    created_at: datetime


class ActionPayload(BaseModel):
    type: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class LearningUpdate(BaseModel):
    status: Literal["created", "updated"]
    pattern_key: str
    usage_count: int


class AgentExecutionResponse(BaseModel):
    request_id: UUID
    conversation_id: UUID
    user_id: UUID
    agent_id: UUID
    mode: Literal["direct", "orchestrator"]
    intent: str
    specialists_used: list[str] = Field(default_factory=list)
    prompt: str
    response_text: str
    structured_action: ActionPayload
    memory_hits: list[str] = Field(default_factory=list)
    learning_update: LearningUpdate
    created_at: datetime