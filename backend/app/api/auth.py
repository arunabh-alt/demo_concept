from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.schemas.auth import AuthResponse, SignInRequest, SignUpRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["auth"])


def build_user_response(user: User) -> UserResponse:
    primary_agent = next((agent for agent in user.agents if agent.is_primary), None)
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        created_at=user.created_at,
        primary_agent_id=primary_agent.id if primary_agent is not None else None,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    user.agents.append(
        AgentProfile(
            name=f"{payload.full_name.strip()} Digital Twin",
            mode_preference="direct",
            role="role_agent",
            is_primary=True,
            description="Primary digital twin agent for the user.",
        )
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id))
    return AuthResponse(access_token=token, user=build_user_response(user))


@router.post("/signin", response_model=AuthResponse)
def signin(payload: SignInRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id))
    return AuthResponse(access_token=token, user=build_user_response(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return build_user_response(current_user)
