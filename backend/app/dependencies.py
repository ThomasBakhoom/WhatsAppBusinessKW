"""Shared FastAPI dependencies."""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

logger = structlog.get_logger()

security_scheme = HTTPBearer()


class CurrentUser:
    """Represents the authenticated user from a JWT token."""

    def __init__(
        self,
        user_id: UUID,
        company_id: UUID,
        roles: list[str],
        permissions: list[str],
    ):
        self.user_id = user_id
        self.company_id = company_id
        self.roles = roles
        self.permissions = permissions


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> CurrentUser:
    """Extract and validate the current user from the JWT token."""
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Build permissions from roles
    from app.core.permissions import ROLE_PERMISSIONS

    roles = payload.get("roles", [])
    permissions: set[str] = set()
    for role in roles:
        role_perms = ROLE_PERMISSIONS.get(role, [])
        permissions.update(p.value for p in role_perms)

    return CurrentUser(
        user_id=UUID(payload["sub"]),
        company_id=UUID(payload["company_id"]),
        roles=roles,
        permissions=list(permissions),
    )


async def get_tenant_db(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> AsyncSession:
    """Get a database session with RLS tenant context set."""
    # asyncpg doesn't support params in SET LOCAL, so we use a safe literal.
    # company_id is already validated as UUID from the JWT, so this is safe.
    tenant_id = str(current_user.company_id)
    await db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    return db


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
TenantDbSession = Annotated[AsyncSession, Depends(get_tenant_db)]
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
