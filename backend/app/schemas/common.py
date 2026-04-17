"""Common schemas shared across modules."""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base model that converts snake_case to camelCase in JSON output."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"


class ErrorResponse(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    errors: list[dict[str, Any]] | None = None
    trace_id: str | None = None


class PaginatedMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool
    next_cursor: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginatedMeta
