from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for pagination."""

    limit: int = 20
    offset: int = 0
    cursor: str | None = None
    sort: str = "-created_at"

    def get_sort_field(self) -> str:
        """Get the sort field name without direction prefix."""
        return self.sort.lstrip("-+")

    def is_descending(self) -> bool:
        """Check if sort direction is descending."""
        return self.sort.startswith("-")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    data: list[T]
    meta: dict[str, Any]

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        limit: int,
        offset: int,
        next_cursor: str | None = None,
    ) -> "PaginatedResponse[T]":
        return cls(
            data=items,
            meta={
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
                "next_cursor": next_cursor,
            },
        )
