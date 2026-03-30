from pydantic import BaseModel, Field


class AgentExecutionRequest(BaseModel):
    user_id: str = Field(min_length=2)
    agent_id: str = Field(min_length=2)
    message: str = Field(min_length=1)
