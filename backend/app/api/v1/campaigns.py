"""Campaign/Broadcast API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Query
from app.core.pagination import PaginatedResponse
from app.dependencies import AuthUser, TenantDbSession
from app.schemas.campaigns import CampaignCreate, CampaignResponse, CampaignStats, CampaignUpdate
from app.schemas.common import SuccessResponse
from app.services.campaign_service import CampaignService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CampaignResponse])
async def list_campaigns(db: TenantDbSession, user: AuthUser,
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    svc = CampaignService(db, user.company_id)
    items, total = await svc.list_campaigns(limit=limit, offset=offset)
    return PaginatedResponse.create(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(data: CampaignCreate, db: TenantDbSession, user: AuthUser):
    svc = CampaignService(db, user.company_id)
    c = await svc.create_campaign(data, user_id=user.user_id)
    await db.commit()
    return c


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: UUID, db: TenantDbSession, user: AuthUser):
    return await CampaignService(db, user.company_id).get_campaign(campaign_id)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: UUID, data: CampaignUpdate, db: TenantDbSession, user: AuthUser):
    svc = CampaignService(db, user.company_id)
    c = await svc.update_campaign(campaign_id, data)
    await db.commit()
    return c


@router.delete("/{campaign_id}", response_model=SuccessResponse)
async def delete_campaign(campaign_id: UUID, db: TenantDbSession, user: AuthUser):
    await CampaignService(db, user.company_id).delete_campaign(campaign_id)
    await db.commit()
    return SuccessResponse(message="Campaign deleted")


@router.post("/{campaign_id}/send", response_model=CampaignResponse)
async def send_campaign(campaign_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = CampaignService(db, user.company_id)
    c = await svc.send_campaign(campaign_id)
    await db.commit()
    return c


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(campaign_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = CampaignService(db, user.company_id)
    c = await svc.pause_campaign(campaign_id)
    await db.commit()
    return c


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(campaign_id: UUID, db: TenantDbSession, user: AuthUser):
    return await CampaignService(db, user.company_id).get_stats(campaign_id)
