from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.user import User


class ActionExecution(Base):
    __tablename__ = "action_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agent_profiles.id"), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    request_message: Mapped[str] = mapped_column(Text(), nullable=False)
    intent: Mapped[str] = mapped_column(String(80), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[float | None] = mapped_column(Float(), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    beneficiary_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    response_payload: Mapped[dict] = mapped_column(JSON(), nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="action_executions")
    agent: Mapped["AgentProfile"] = relationship(back_populates="action_executions")