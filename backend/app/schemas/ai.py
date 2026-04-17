"""Schemas for AI engine."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


class AIContextResponse(CamelModel):
    id: UUID
    conversation_id: UUID
    detected_dialect: str | None = None
    current_intent: str | None = None
    intent_confidence: float | None = None
    sentiment: str | None = None
    sentiment_score: float | None = None
    topic: str | None = None
    summary: str | None = None
    suggested_response: str | None = None
    customer_insights: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AIAnalyzeRequest(CamelModel):
    conversation_id: UUID
    message_content: str
    message_direction: str = "inbound"


class AIAnalyzeResponse(CamelModel):
    dialect: str | None = None
    intent: str | None = None
    intent_confidence: float | None = None
    sentiment: str | None = None
    sentiment_score: float | None = None
    topic: str | None = None
    suggested_response: str | None = None
    customer_insights: dict[str, Any] = Field(default_factory=dict)


class AISettingsUpdate(CamelModel):
    auto_detect_dialect: bool | None = None
    auto_classify_intent: bool | None = None
    auto_suggest_replies: bool | None = None
    ai_language: str | None = None  # en, ar, auto


class AISettingsResponse(CamelModel):
    auto_detect_dialect: bool = True
    auto_classify_intent: bool = True
    auto_suggest_replies: bool = True
    ai_language: str = "auto"
