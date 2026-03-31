from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.schemas.agentic import AgentExecutionRequest, AgentExecutionResponse, AgentProfileResponse
from app.services.agentic_orchestrator import AgentExecutionService


router = APIRouter(prefix="/agents", tags=["agents"])
execution_service = AgentExecutionService()


@router.get("/mine", response_model=list[AgentProfileResponse])
def list_my_agents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AgentProfileResponse]:
    agents = db.scalars(select(AgentProfile).where(AgentProfile.user_id == current_user.id)).all()
    return [AgentProfileResponse.model_validate(agent) for agent in agents]


@router.post("/execute", response_model=AgentExecutionResponse)
def execute_agent(
    payload: AgentExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentExecutionResponse:
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user_id does not match authenticated user")

    try:
        return execution_service.execute(db=db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc