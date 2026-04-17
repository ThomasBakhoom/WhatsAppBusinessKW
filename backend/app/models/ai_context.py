"""AI conversation context model - tracks dialect, intent, sentiment per conversation."""

import uuid

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class AIConversationContext(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Stores AI analysis context for a conversation."""

    __tablename__ = "ai_conversation_contexts"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Dialect detection
    detected_dialect: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # kuwaiti, gulf, msa, english, mixed

    # Intent classification
    current_intent: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # inquiry, purchase, support, complaint, greeting, scheduling, pricing, other

    intent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Sentiment
    sentiment: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # positive, negative, neutral, mixed

    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to 1.0

    # Topic/category
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Summary of conversation so far
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Suggested response (AI-generated)
    suggested_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full context history for AI continuity
    context_history: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )  # [{role, content, timestamp}, ...]

    # Customer profile insights extracted by AI
    customer_insights: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )  # {needs, preferences, budget_range, urgency}

    def __repr__(self) -> str:
        return f"<AIContext conv={self.conversation_id} dialect={self.detected_dialect}>"
