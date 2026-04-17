"""Schemas for pipelines, stages, and deals."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


# ── Pipeline Stages ───────────────────────────────────────────────────────────

class StageCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    sort_order: int = 0
    is_won: bool = False
    is_lost: bool = False


class StageResponse(CamelModel):
    id: UUID
    name: str
    color: str
    sort_order: int
    is_won: bool
    is_lost: bool


# ── Pipelines ─────────────────────────────────────────────────────────────────

class PipelineCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    is_default: bool = False
    stages: list[StageCreate] = Field(default_factory=list)


class PipelineUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class PipelineResponse(CamelModel):
    id: UUID
    name: str
    description: str | None = None
    is_default: bool
    is_active: bool
    stages: list[StageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ── Deals ─────────────────────────────────────────────────────────────────────

class DealCreate(CamelModel):
    pipeline_id: UUID
    stage_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    value: Decimal = Field(default=Decimal("0.000"), ge=0)
    currency: str = Field(default="KWD", max_length=3)
    contact_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    expected_close_date: datetime | None = None
    custom_data: dict[str, Any] = Field(default_factory=dict)


class DealUpdate(CamelModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    value: Decimal | None = Field(default=None, ge=0)
    stage_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    expected_close_date: datetime | None = None
    status: str | None = Field(default=None, pattern=r"^(open|won|lost)$")
    position: int | None = None
    custom_data: dict[str, Any] | None = None


class DealMoveRequest(CamelModel):
    stage_id: UUID
    position: int = 0


class DealResponse(CamelModel):
    id: UUID
    pipeline_id: UUID
    stage_id: UUID | None = None
    stage: StageResponse | None = None
    title: str
    description: str | None = None
    value: Decimal
    currency: str
    status: str
    contact_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    expected_close_date: datetime | None = None
    closed_at: datetime | None = None
    position: int
    custom_data: dict[str, Any]
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class DealActivityResponse(CamelModel):
    id: UUID
    deal_id: UUID
    activity_type: str
    description: str
    user_id: UUID | None = None
    old_value: str | None = None
    new_value: str | None = None
    created_at: datetime


# ── Kanban Board ──────────────────────────────────────────────────────────────

class KanbanColumn(CamelModel):
    stage: StageResponse
    deals: list[DealResponse] = Field(default_factory=list)
    total_value: Decimal = Decimal("0.000")
    deal_count: int = 0


class KanbanBoard(CamelModel):
    pipeline: PipelineResponse
    columns: list[KanbanColumn] = Field(default_factory=list)
