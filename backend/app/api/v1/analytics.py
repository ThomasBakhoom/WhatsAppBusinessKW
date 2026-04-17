"""Analytics API endpoints."""

from fastapi import APIRouter, Query

from app.dependencies import AuthUser, TenantDbSession
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    db: TenantDbSession,
    user: AuthUser,
    days: int = Query(default=30, ge=1, le=365),
):
    """Top-level dashboard stats."""
    svc = AnalyticsService(db, user.company_id)
    return await svc.get_dashboard(days)


@router.get("/messages")
async def get_message_stats(
    db: TenantDbSession,
    user: AuthUser,
    days: int = Query(default=30, ge=1, le=365),
):
    """Message volume and delivery stats."""
    svc = AnalyticsService(db, user.company_id)
    return await svc.get_message_stats(days)


@router.get("/pipeline")
async def get_pipeline_stats(db: TenantDbSession, user: AuthUser):
    """Pipeline deal analytics."""
    svc = AnalyticsService(db, user.company_id)
    return await svc.get_pipeline_stats()


@router.get("/team")
async def get_team_stats(
    db: TenantDbSession,
    user: AuthUser,
    days: int = Query(default=30, ge=1, le=365),
):
    """Per-agent performance."""
    svc = AnalyticsService(db, user.company_id)
    return await svc.get_team_stats(days)


@router.get("/landing-pages")
async def get_landing_page_stats(db: TenantDbSession, user: AuthUser):
    """Landing page conversion stats."""
    svc = AnalyticsService(db, user.company_id)
    return await svc.get_landing_page_stats()


@router.get("/automations")
async def get_automation_stats(db: TenantDbSession, user: AuthUser):
    """Automation execution stats."""
    svc = AnalyticsService(db, user.company_id)
    return await svc.get_automation_stats()
