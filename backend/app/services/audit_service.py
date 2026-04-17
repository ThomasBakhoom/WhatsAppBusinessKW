"""Audit log service."""

from datetime import datetime, timedelta, timezone
from typing import Any, TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

if TYPE_CHECKING:
    from app.services.actor import Actor


logger = structlog.get_logger()


class AuditService:
    def __init__(
        self,
        db: AsyncSession,
        company_id: UUID,
        actor: "Actor | None" = None,
    ):
        self.db = db
        self.company_id = company_id
        self.actor = actor

    async def log(
        self,
        action: str,
        description: str,
        *,
        user_id: UUID | None = None,
        user_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog | None:
        """Write an audit log entry.

        Best-effort: a failing audit write is logged as a warning but does not
        break the caller's transaction. If an `actor` was set on construction,
        its fields are used as defaults for user_id/user_email/ip/ua so service
        code can call `await audit.log(action, description, resource_type=..., resource_id=...)`
        without re-passing the actor every time.
        """
        if self.actor is not None:
            user_id = user_id or self.actor.user_id
            user_email = user_email or self.actor.user_email
            ip_address = ip_address or self.actor.ip_address
            user_agent = user_agent or self.actor.user_agent

        try:
            entry = AuditLog(
                company_id=self.company_id,
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.add(entry)
            await self.db.flush()
            return entry
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audit_log_failed", action=action, error=str(exc))
            return None

    async def get_logs(
        self,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        user_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        base = select(AuditLog).where(AuditLog.company_id == self.company_id)
        if action:
            base = base.where(AuditLog.action == action)
        if resource_type:
            base = base.where(AuditLog.resource_type == resource_type)
        if user_id:
            base = base.where(AuditLog.user_id == user_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        query = base.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)

        items = [
            {
                "id": str(log.id),
                "action": log.action,
                "description": log.description,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": log.user_email,
                "changes": log.changes,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in result.scalars().all()
        ]
        return items, total
