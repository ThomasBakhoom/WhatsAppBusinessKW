"""Schemas for campaigns/broadcasts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field
from app.schemas.common import CamelModel


class CampaignCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    message_type: str = Field(default="template", pattern=r"^(template|text)$")
    template_name: str | None = None
    template_language: str = "en"
    message_body: str | None = None
    media_url: str | None = None
    audience_type: str = Field(default="all", pattern=r"^(all|tag|segment|custom)$")
    audience_filter: dict[str, Any] = Field(default_factory=dict)
    scheduled_at: datetime | None = None


class CampaignUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    message_body: str | None = None
    template_name: str | None = None
    audience_filter: dict[str, Any] | None = None
    scheduled_at: datetime | None = None


class CampaignResponse(CamelModel):
    id: UUID
    name: str
    description: str | None = None
    status: str
    message_type: str
    template_name: str | None = None
    template_language: str
    message_body: str | None = None
    audience_type: str
    audience_filter: dict[str, Any]
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_recipients: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int
    reply_count: int
    created_at: datetime
    updated_at: datetime


class CampaignStats(CamelModel):
    total: int
    sent: int
    delivered: int
    read: int
    failed: int
    delivery_rate: float
    read_rate: float
