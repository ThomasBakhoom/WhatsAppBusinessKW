"""Schemas for chatbot flow builder."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import Field
from app.schemas.common import CamelModel


class FlowNode(CamelModel):
    id: str
    type: str  # send_message, ask_question, condition, action, delay, assign_agent, api_call
    position: dict[str, float]  # {x, y}
    data: dict[str, Any] = Field(default_factory=dict)


class FlowEdge(CamelModel):
    id: str
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None
    label: str | None = None


class ChatbotFlowCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    trigger_type: str = Field(default="keyword", pattern=r"^(keyword|message_received|conversation_started|webhook)$")
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    nodes: list[FlowNode] = Field(default_factory=list)
    edges: list[FlowEdge] = Field(default_factory=list)


class ChatbotFlowUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    trigger_config: dict[str, Any] | None = None
    nodes: list[FlowNode] | None = None
    edges: list[FlowEdge] | None = None
    is_active: bool | None = None


class ChatbotFlowResponse(CamelModel):
    id: UUID
    name: str
    description: str | None = None
    is_active: bool
    trigger_type: str
    trigger_config: dict[str, Any]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    execution_count: int
    created_at: datetime
    updated_at: datetime
