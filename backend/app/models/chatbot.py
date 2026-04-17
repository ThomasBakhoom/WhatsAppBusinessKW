"""Chatbot flow builder models - visual node/edge based flows."""

import uuid
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class ChatbotFlow(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A visual chatbot flow (node/edge graph)."""

    __tablename__ = "chatbot_flows"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Trigger: keyword, message_received, conversation_started, webhook
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False, default="keyword")
    trigger_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # e.g., {"keywords": ["menu", "help"], "match_type": "contains"}

    # Visual graph (React Flow format)
    # nodes: [{id, type, position: {x,y}, data: {...}}]
    # edges: [{id, source, target, sourceHandle, targetHandle}]
    nodes: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    edges: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    # Stats
    execution_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    def __repr__(self) -> str:
        return f"<ChatbotFlow {self.name}>"
