"""Schemas for automations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


class AutomationActionCreate(CamelModel):
    action_type: str = Field(..., pattern=r"^(send_message|assign_agent|add_tag|remove_tag|change_status|update_lead_score|send_template|webhook|auto_reply)$")
    config: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0


class AutomationActionResponse(CamelModel):
    id: UUID
    action_type: str
    config: dict[str, Any]
    sort_order: int


class ConditionItem(CamelModel):
    field: str  # e.g., "message.content", "contact.status", "contact.tag"
    operator: str  # equals, not_equals, contains, starts_with, gt, lt, in
    value: Any


class AutomationCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    trigger_event: str = Field(..., pattern=r"^(message\.received|contact\.created|contact\.updated|conversation\.created|deal\.stage_changed)$")
    conditions: list[ConditionItem] = Field(default_factory=list)
    actions: list[AutomationActionCreate] = Field(..., min_length=1)
    priority: int = 0
    is_active: bool = True


class AutomationUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    conditions: list[ConditionItem] | None = None
    actions: list[AutomationActionCreate] | None = None
    priority: int | None = None
    is_active: bool | None = None


class AutomationResponse(CamelModel):
    id: UUID
    name: str
    description: str | None = None
    is_active: bool
    trigger_event: str
    conditions: list[dict[str, Any]]
    actions: list[AutomationActionResponse] = Field(default_factory=list)
    priority: int
    execution_count: int
    last_executed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AutomationLogResponse(CamelModel):
    id: UUID
    automation_id: UUID
    trigger_event: str
    trigger_data: dict[str, Any]
    status: str
    actions_executed: int
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: datetime
