"""Platform-admin routes (cross-tenant).

Only users with the `platform_admin` role can access these endpoints.
They bypass the per-tenant RLS filter so the operator can:

  * See an aggregate overview across all companies
  * List / view / suspend / activate any company
  * List all users across tenants
  * Impersonate a company owner (for support) by issuing a JWT
    scoped to that company

Security note: impersonation writes an audit_log entry for every use.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, create_refresh_token
from app.dependencies_platform import PlatformDbSession, PlatformUser
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.payment import Subscription
from app.models.auth import Role, User, UserRole

logger = structlog.get_logger()
router = APIRouter()


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/overview")
async def platform_overview(
    db: PlatformDbSession,
    user: PlatformUser,
):
    """Aggregate stats across ALL tenants.

    Intended for the platform dashboard landing page. All counts are
    live; no caching layer. If the system grows beyond ~10K companies
    you'll want to denormalise these into a nightly rollup table.
    """
    companies_count = (await db.execute(select(func.count(Company.id)))).scalar_one()
    active_companies = (
        await db.execute(select(func.count(Company.id)).where(Company.is_active == True))  # noqa: E712
    ).scalar_one()
    users_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    contacts_count = (
        await db.execute(
            select(func.count(Contact.id)).where(Contact.deleted_at.is_(None))
        )
    ).scalar_one()
    conversations_count = (
        await db.execute(select(func.count(Conversation.id)))
    ).scalar_one()
    messages_count = (await db.execute(select(func.count(Message.id)))).scalar_one()
    subscriptions_active = (
        await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
    ).scalar_one()

    # Growth: companies registered in the last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    new_companies_30d = (
        await db.execute(
            select(func.count(Company.id)).where(Company.created_at >= thirty_days_ago)
        )
    ).scalar_one()

    return {
        "companies": {
            "total": companies_count,
            "active": active_companies,
            "new_last_30d": new_companies_30d,
        },
        "users": {"total": users_count},
        "data": {
            "contacts": contacts_count,
            "conversations": conversations_count,
            "messages": messages_count,
        },
        "subscriptions": {"active": subscriptions_active},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Companies ─────────────────────────────────────────────────────────────────

@router.get("/companies")
async def list_companies(
    db: PlatformDbSession,
    user: PlatformUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(None),
):
    """Paginated list of ALL companies across the platform."""
    base = select(Company)
    if search:
        term = f"%{search}%"
        base = base.where((Company.name.ilike(term)) | (Company.slug.ilike(term)))
    if is_active is not None:
        base = base.where(Company.is_active == is_active)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    q = base.order_by(desc(Company.created_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    rows = result.scalars().all()

    return {
        "data": [
            {
                "id": str(c.id),
                "name": c.name,
                "slug": c.slug,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
                "whatsapp_connected": bool(c.whatsapp_phone_number_id),
            }
            for c in rows
        ],
        "meta": {"total": total, "limit": limit, "offset": offset, "has_more": offset + limit < total},
    }


@router.get("/companies/{company_id}")
async def get_company_detail(
    company_id: UUID,
    db: PlatformDbSession,
    user: PlatformUser,
):
    """Deep view of a single company: metadata + per-tenant counts."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Per-tenant counts. We scope every count by company_id explicitly
    # because RLS is bypassed here.
    user_count = (
        await db.execute(select(func.count(User.id)).where(User.company_id == company_id))
    ).scalar_one()
    contact_count = (
        await db.execute(
            select(func.count(Contact.id)).where(
                Contact.company_id == company_id, Contact.deleted_at.is_(None)
            )
        )
    ).scalar_one()
    conv_count = (
        await db.execute(
            select(func.count(Conversation.id)).where(Conversation.company_id == company_id)
        )
    ).scalar_one()
    msg_count = (
        await db.execute(
            select(func.count(Message.id)).where(Message.company_id == company_id)
        )
    ).scalar_one()
    sub_result = await db.execute(
        select(Subscription)
        .where(Subscription.company_id == company_id)
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    subscription = sub_result.scalar_one_or_none()

    # Latest 10 audit entries for this company
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.company_id == company_id)
        .order_by(desc(AuditLog.created_at))
        .limit(10)
    )
    recent_audit = [
        {
            "action": a.action,
            "description": a.description,
            "user_email": a.user_email,
            "ip_address": a.ip_address,
            "created_at": a.created_at.isoformat(),
        }
        for a in audit_result.scalars().all()
    ]

    return {
        "id": str(company.id),
        "name": company.name,
        "slug": company.slug,
        "is_active": company.is_active,
        "whatsapp_connected": bool(company.whatsapp_phone_number_id),
        "settings": company.settings or {},
        "created_at": company.created_at.isoformat(),
        "updated_at": company.updated_at.isoformat(),
        "stats": {
            "users": user_count,
            "contacts": contact_count,
            "conversations": conv_count,
            "messages": msg_count,
        },
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status,
            "billing_cycle": subscription.billing_cycle,
            "current_period_end": subscription.current_period_end.isoformat()
                if subscription.current_period_end else None,
        } if subscription else None,
        "recent_audit": recent_audit,
    }


@router.post("/companies/{company_id}/suspend")
async def suspend_company(
    company_id: UUID,
    request: Request,
    db: PlatformDbSession,
    user: PlatformUser,
):
    """Flip is_active=false. Blocks all logins from this company.

    The API's login flow checks `user.is_active` but not `company.is_active`
    — this only hides the company from listings today. For full lockout
    you'd need to add a `Company.is_active` check in `auth_service.login`.
    """
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.is_active:
        return {"status": "already_suspended", "company_id": str(company_id)}

    company.is_active = False

    # Audit under the target company so it's visible in their log too
    _audit(
        db,
        company_id=company_id,
        action="platform.company_suspended",
        description=f"Company '{company.name}' suspended by platform admin",
        user_id=user.user_id,
    )
    await db.commit()
    return {"status": "suspended", "company_id": str(company_id)}


@router.post("/companies/{company_id}/activate")
async def activate_company(
    company_id: UUID,
    request: Request,
    db: PlatformDbSession,
    user: PlatformUser,
):
    """Re-activate a previously suspended company."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.is_active:
        return {"status": "already_active", "company_id": str(company_id)}

    company.is_active = True
    _audit(
        db,
        company_id=company_id,
        action="platform.company_activated",
        description=f"Company '{company.name}' re-activated by platform admin",
        user_id=user.user_id,
    )
    await db.commit()
    return {"status": "active", "company_id": str(company_id)}


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users_cross_tenant(
    db: PlatformDbSession,
    user: PlatformUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    company_id: UUID | None = Query(None),
):
    """List users across ALL companies, with company info joined in."""
    base = select(User, Company.name.label("company_name"), Company.slug.label("company_slug")).join(
        Company, User.company_id == Company.id
    )
    if search:
        term = f"%{search}%"
        base = base.where(
            (User.email.ilike(term))
            | (User.username.ilike(term))
            | (User.first_name.ilike(term))
            | (User.last_name.ilike(term))
        )
    if company_id:
        base = base.where(User.company_id == company_id)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    q = base.order_by(desc(User.created_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    rows = result.all()

    return {
        "data": [
            {
                "id": str(u.id),
                "email": u.email,
                "username": u.username,
                "full_name": f"{u.first_name} {u.last_name}".strip(),
                "is_active": u.is_active,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "created_at": u.created_at.isoformat(),
                "company": {
                    "id": str(u.company_id),
                    "name": company_name,
                    "slug": company_slug,
                },
            }
            for u, company_name, company_slug in rows
        ],
        "meta": {"total": total, "limit": limit, "offset": offset, "has_more": offset + limit < total},
    }


# ── Impersonation ─────────────────────────────────────────────────────────────

@router.post("/impersonate/{company_id}")
async def impersonate_company_owner(
    company_id: UUID,
    request: Request,
    db: PlatformDbSession,
    user: PlatformUser,
):
    """Issue a JWT that makes the platform admin appear as an owner of
    `company_id` for support / troubleshooting purposes.

    Security:
      * Token has a SHORT expiry (15 min) regardless of the default refresh
      * Audit entry written under BOTH the platform admin AND the target company
      * The returned JWT carries `platform_admin` + `owner` roles so the
        admin can still access /platform routes AND the target company's data
    """
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Find any active owner of the target company (for user_id in the token)
    owner_result = await db.execute(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(User.company_id == company_id, Role.name == "owner", User.is_active == True)  # noqa: E712
        .limit(1)
    )
    target_owner = owner_result.scalar_one_or_none()
    if not target_owner:
        raise HTTPException(
            status_code=404,
            detail="No active owner found in target company; cannot impersonate",
        )

    # Craft a token that carries BOTH roles.
    token_roles = ["platform_admin", "owner"]
    access_token = create_access_token(
        user_id=target_owner.id,
        company_id=company_id,
        roles=token_roles,
        expires_delta=timedelta(minutes=15),
    )
    refresh_token = create_refresh_token(user_id=target_owner.id)

    _audit(
        db,
        company_id=company_id,
        action="platform.impersonation_started",
        description=f"Platform admin impersonated {target_owner.email}",
        user_id=user.user_id,
        user_email=None,
    )
    await db.commit()

    logger.info(
        "platform_impersonation",
        platform_admin_id=str(user.user_id),
        target_user_id=str(target_owner.id),
        target_company_id=str(company_id),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 15 * 60,
        "impersonating": {
            "company_id": str(company_id),
            "company_name": company.name,
            "user_id": str(target_owner.id),
            "user_email": target_owner.email,
        },
    }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _audit(
    db,
    *,
    company_id: UUID,
    action: str,
    description: str,
    user_id: UUID | None = None,
    user_email: str | None = None,
) -> None:
    """Inline audit helper. Uses the platform db session which can write to
    any company's audit_logs (RLS bypassed)."""
    db.add(
        AuditLog(
            company_id=company_id,
            user_id=user_id,
            user_email=user_email,
            action=action,
            description=description,
            resource_type="company",
            resource_id=str(company_id),
        )
    )
