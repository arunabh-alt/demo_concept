from appbank_digital_twin.schemas.requests import AgentExecutionRequest
from appbank_digital_twin.schemas.responses import AgentExecutionResponse


class OrchestratorService:
    def plan(self, request: AgentExecutionRequest) -> AgentExecutionResponse:
        mode = "direct" if len(request.message.split()) < 25 else "orchestrator"
        return AgentExecutionResponse(
            mode=mode,
            accepted=True,
            proposed_action=f"Analyze request for user {request.user_id} and generate a verifier-ready plan.",
            verifier_status="pending",
            next_step="Implement the verifier pipeline before enabling real execution.",
        )