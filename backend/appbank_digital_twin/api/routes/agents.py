from fastapi import APIRouter

from appbank_digital_twin.schemas.requests import AgentExecutionRequest
from appbank_digital_twin.schemas.responses import AgentExecutionResponse
from appbank_digital_twin.services.orchestrator import OrchestratorService


router = APIRouter(tags=["agents"])
orchestrator_service = OrchestratorService()


@router.post("/agent/execute", response_model=AgentExecutionResponse)
def execute_agent(request: AgentExecutionRequest) -> AgentExecutionResponse:
    return orchestrator_service.plan(request)
