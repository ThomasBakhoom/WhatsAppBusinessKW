"""Compliance and audit API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.pagination import PaginatedResponse
from app.dependencies import AuthUser, TenantDbSession
from app.services.audit_service import AuditService
from app.services.compliance_service import ComplianceService

router = APIRouter()


@router.get("/status")
async def get_compliance_status(db: TenantDbSession, user: AuthUser):
    """Get compliance checklist status."""
    svc = ComplianceService(db, user.company_id)
    return await svc.get_compliance_status()


@router.get("/report")
async def get_compliance_report(db: TenantDbSession, user: AuthUser):
    """Generate full compliance report."""
    svc = ComplianceService(db, user.company_id)
    return await svc.generate_report()


@router.get("/audit-logs")
async def get_audit_logs(
    db: TenantDbSession,
    user: AuthUser,
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Get audit log entries."""
    svc = AuditService(db, user.company_id)
    items, total = await svc.get_logs(
        action=action, resource_type=resource_type, limit=limit, offset=offset
    )
    return PaginatedResponse.create(items=items, total=total, limit=limit, offset=offset)
