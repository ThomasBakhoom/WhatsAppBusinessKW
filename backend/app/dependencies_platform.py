"""Platform-admin only dependencies and helpers.

Platform admin is a cross-tenant role. Unlike company owners/admins who
operate within a single `company_id`, a platform admin can query across
all tenants. These dependencies enforce:

  1. The caller holds the `platform_admin` role in their JWT.
  2. The DB session bypasses RLS so cross-tenant queries work.

The second point is achieved by NOT calling `set_tenant_context()` on the
session — the runtime DB user (`app_user` or the Railway default
postgres user) handles the visibility. In Railway's default setup the
connection runs as a superuser that bypasses RLS naturally; on a
properly locked-down deploy you'd add a SECURITY DEFINER helper or a
dedicated BYPASSRLS role for this purpose.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser, get_current_user


async def require_platform_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Dependency that rejects any request lacking the `platform_admin` role."""
    if "platform_admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin role required",
        )
    return current_user


async def get_platform_db(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_platform_admin)],
) -> AsyncSession:
    """Get an RLS-bypassing session for cross-tenant platform queries.

    We intentionally do NOT call `set_tenant_context()` so the session
    has no `app.current_tenant` GUC. The hardened RLS policy returns
    NULL when the GUC is unset, which filters rows to zero for
    non-superuser roles. In production you must run this as a role with
    BYPASSRLS or replace the queries with SECURITY DEFINER helpers.
    """
    return db


# Type aliases for dependency injection
PlatformUser = Annotated[CurrentUser, Depends(require_platform_admin)]
PlatformDbSession = Annotated[AsyncSession, Depends(get_platform_db)]
