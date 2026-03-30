from typing import Literal

from pydantic import BaseModel


class AgentExecutionResponse(BaseModel):
    mode: Literal["direct", "orchestrator"]
    accepted: bool
    proposed_action: str
    verifier_status: Literal["pending", "approved", "rejected"]
    next_step: str
