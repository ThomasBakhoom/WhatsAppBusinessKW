"""Automation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import AuthUser, TenantDbSession
from app.schemas.automations import (
    AutomationCreate,
    AutomationLogResponse,
    AutomationResponse,
    AutomationUpdate,
)
from app.schemas.common import SuccessResponse
from app.services.automation_service import AutomationService

router = APIRouter()


@router.get("", response_model=list[AutomationResponse])
async def list_automations(
    db: TenantDbSession,
    user: AuthUser,
):
    svc = AutomationService(db, user.company_id)
    return await svc.list_automations()


@router.post("", response_model=AutomationResponse, status_code=201)
async def create_automation(
    data: AutomationCreate,
    db: TenantDbSession,
    user: AuthUser,
):
    svc = AutomationService(db, user.company_id)
    auto = await svc.create_automation(data)
    await db.commit()
    return auto


@router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
):
    svc = AutomationService(db, user.company_id)
    return await svc.get_automation(automation_id)


@router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: UUID,
    data: AutomationUpdate,
    db: TenantDbSession,
    user: AuthUser,
):
    svc = AutomationService(db, user.company_id)
    auto = await svc.update_automation(automation_id, data)
    await db.commit()
    return auto


@router.delete("/{automation_id}", response_model=SuccessResponse)
async def delete_automation(
    automation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
):
    svc = AutomationService(db, user.company_id)
    await svc.delete_automation(automation_id)
    await db.commit()
    return SuccessResponse(message="Automation deleted")


@router.post("/{automation_id}/toggle", response_model=AutomationResponse)
async def toggle_automation(
    automation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
):
    svc = AutomationService(db, user.company_id)
    auto = await svc.toggle_automation(automation_id)
    await db.commit()
    return auto


@router.get("/{automation_id}/logs", response_model=list[AutomationLogResponse])
async def get_automation_logs(
    automation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    limit: int = Query(default=50, ge=1, le=200),
):
    svc = AutomationService(db, user.company_id)
    return await svc.get_logs(automation_id, limit=limit)
