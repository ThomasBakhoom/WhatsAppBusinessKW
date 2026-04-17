"""Lightweight `Actor` abstraction for service-level audit attribution.

Threading `user_id`, `ip_address` and `user_agent` through every service
method signature would explode the API surface. Instead, services accept an
optional `actor: Actor | None` in the constructor and use it for all audit
calls within that service instance.

Routes build an Actor from the JWT-authenticated `CurrentUser` plus the raw
`Request` (for IP/UA), then hand it to the service alongside `db` and
`company_id`. Services that don't get an Actor (background tasks, system
operations) skip the attribution gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Request

from app.dependencies import CurrentUser


@dataclass(slots=True, frozen=True)
class Actor:
    """Who performed an action, captured for audit logs."""

    user_id: UUID | None = None
    user_email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


def actor_from_request(user: CurrentUser, request: Request) -> Actor:
    """Build an Actor from the FastAPI request + authenticated user.

    Honors X-Forwarded-For when present (first hop is the real client).
    Note: `user_email` is not in the JWT — audit consumers can join to
    `users` via `user_id` to render the email.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip() or None
    else:
        ip = request.client.host if request.client else None
    return Actor(
        user_id=user.user_id,
        user_email=None,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
