"""CSAT/Survey models."""

import uuid
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Survey(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "surveys"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    survey_type: Mapped[str] = mapped_column(String(20), nullable=False, default="csat")  # csat, nps, custom
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    trigger: Mapped[str] = mapped_column(String(50), nullable=False, default="conversation_closed")
    total_responses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Survey {self.name}>"


class SurveyResponse(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "survey_responses"

    survey_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
