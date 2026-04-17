"""Pipeline and deal API endpoints."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.pagination import PaginatedResponse
from app.dependencies import AuthUser, TenantDbSession
from app.schemas.common import SuccessResponse
from app.schemas.pipelines import (
    DealActivityResponse,
    DealCreate,
    DealMoveRequest,
    DealResponse,
    DealUpdate,
    KanbanBoard,
    PipelineCreate,
    PipelineResponse,
    PipelineUpdate,
    StageCreate,
    StageResponse,
)
from app.services.actor import actor_from_request
from app.services.pipeline_service import PipelineService

router = APIRouter()


# ── Pipelines ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id)
    return await svc.list_pipelines()


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(data: PipelineCreate, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    pipeline = await svc.create_pipeline(data)
    await db.commit()
    return pipeline


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id)
    return await svc.get_pipeline(pipeline_id)


@router.patch("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: UUID, data: PipelineUpdate, request: Request, db: TenantDbSession, user: AuthUser
):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    pipeline = await svc.update_pipeline(pipeline_id, data)
    await db.commit()
    return pipeline


@router.delete("/{pipeline_id}", response_model=SuccessResponse)
async def delete_pipeline(pipeline_id: UUID, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    await svc.delete_pipeline(pipeline_id)
    await db.commit()
    return SuccessResponse(message="Pipeline deleted")


# ── Stages ────────────────────────────────────────────────────────────────────


@router.post("/{pipeline_id}/stages", response_model=StageResponse, status_code=201)
async def add_stage(pipeline_id: UUID, data: StageCreate, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    stage = await svc.add_stage(pipeline_id, data)
    await db.commit()
    return stage


@router.delete("/stages/{stage_id}", response_model=SuccessResponse)
async def delete_stage(stage_id: UUID, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    await svc.delete_stage(stage_id)
    await db.commit()
    return SuccessResponse(message="Stage deleted")


# ── Kanban Board ──────────────────────────────────────────────────────────────


@router.get("/{pipeline_id}/board", response_model=KanbanBoard)
async def get_kanban_board(pipeline_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id)
    return await svc.get_kanban_board(pipeline_id)


# ── Deals ─────────────────────────────────────────────────────────────────────


@router.get("/{pipeline_id}/deals", response_model=PaginatedResponse[DealResponse])
async def list_deals(
    pipeline_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    stage_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    svc = PipelineService(db, user.company_id)
    items, total = await svc.list_deals(pipeline_id, stage_id=stage_id, status=status, limit=limit, offset=offset)
    return PaginatedResponse.create(items=items, total=total, limit=limit, offset=offset)


@router.post("/deals", response_model=DealResponse, status_code=201)
async def create_deal(data: DealCreate, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    deal = await svc.create_deal(data, user_id=user.user_id)
    await db.commit()
    return deal


@router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id)
    return await svc.get_deal(deal_id)


@router.patch("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(deal_id: UUID, data: DealUpdate, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    deal = await svc.update_deal(deal_id, data, user_id=user.user_id)
    await db.commit()
    return deal


@router.post("/deals/{deal_id}/move", response_model=DealResponse)
async def move_deal(deal_id: UUID, data: DealMoveRequest, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    deal = await svc.move_deal(deal_id, data.stage_id, data.position, user_id=user.user_id)
    await db.commit()
    return deal


@router.delete("/deals/{deal_id}", response_model=SuccessResponse)
async def delete_deal(deal_id: UUID, request: Request, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id, actor=actor_from_request(user, request))
    await svc.delete_deal(deal_id)
    await db.commit()
    return SuccessResponse(message="Deal deleted")


@router.get("/deals/{deal_id}/activities", response_model=list[DealActivityResponse])
async def get_deal_activities(deal_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = PipelineService(db, user.company_id)
    return await svc.get_deal_activities(deal_id)


@router.post("/deals/{deal_id}/notes", response_model=DealActivityResponse, status_code=201)
async def add_deal_note(
    deal_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    note: str = Query(..., min_length=1),
):
    svc = PipelineService(db, user.company_id)
    activity = await svc.add_note(deal_id, note, user_id=user.user_id)
    await db.commit()
    return activity
