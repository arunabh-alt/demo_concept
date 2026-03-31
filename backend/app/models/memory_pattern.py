import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MemoryPattern(Base):
    __tablename__ = "memory_patterns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agent_profiles.id"), nullable=False, index=True)
    pattern_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    pattern_text: Mapped[str] = mapped_column(Text(), nullable=False)
    response_template: Mapped[str | None] = mapped_column(Text(), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="memory_patterns")
    agent: Mapped["AgentProfile"] = relationship(back_populates="memory_patterns")