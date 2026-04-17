"""Pipeline and deal service."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.pipeline import Deal, DealActivity, Pipeline, PipelineStage
from app.schemas.pipelines import (
    DealActivityResponse,
    DealCreate,
    DealResponse,
    DealUpdate,
    KanbanBoard,
    KanbanColumn,
    PipelineCreate,
    PipelineResponse,
    PipelineUpdate,
    StageCreate,
    StageResponse,
)
from app.services.actor import Actor
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class PipelineService:
    def __init__(
        self,
        db: AsyncSession,
        company_id: UUID,
        actor: Actor | None = None,
    ):
        self.db = db
        self.company_id = company_id
        self.actor = actor
        self._audit = AuditService(db, company_id, actor=actor)

    # ── Pipeline CRUD ─────────────────────────────────────────────────────────

    async def list_pipelines(self) -> list[PipelineResponse]:
        result = await self.db.execute(
            select(Pipeline)
            .where(Pipeline.company_id == self.company_id)
            .options(selectinload(Pipeline.stages))
            .order_by(Pipeline.is_default.desc(), Pipeline.name)
        )
        return [self._pipeline_response(p) for p in result.scalars().unique().all()]

    async def get_pipeline(self, pipeline_id: UUID) -> PipelineResponse:
        p = await self._get_pipeline_or_404(pipeline_id)
        return self._pipeline_response(p)

    async def create_pipeline(self, data: PipelineCreate) -> PipelineResponse:
        pipeline = Pipeline(
            company_id=self.company_id,
            name=data.name,
            description=data.description,
            is_default=data.is_default,
        )
        self.db.add(pipeline)
        await self.db.flush()

        for i, stage_data in enumerate(data.stages):
            stage = PipelineStage(
                pipeline_id=pipeline.id,
                name=stage_data.name,
                color=stage_data.color,
                sort_order=stage_data.sort_order or i,
                is_won=stage_data.is_won,
                is_lost=stage_data.is_lost,
            )
            self.db.add(stage)

        await self.db.flush()
        await self._audit.log(
            action="pipeline.created",
            description=f"Pipeline '{pipeline.name}' created with {len(data.stages)} stage(s)",
            resource_type="pipeline",
            resource_id=str(pipeline.id),
            changes={"name": pipeline.name, "is_default": pipeline.is_default},
        )
        return await self.get_pipeline(pipeline.id)

    async def update_pipeline(self, pipeline_id: UUID, data: PipelineUpdate) -> PipelineResponse:
        p = await self._get_pipeline_or_404(pipeline_id)
        update_data = data.model_dump(exclude_unset=True)
        diff: dict[str, dict] = {}
        for key, value in update_data.items():
            old = getattr(p, key, None)
            if old != value:
                diff[key] = {"old": old, "new": value}
            setattr(p, key, value)
        await self.db.flush()
        if diff:
            await self._audit.log(
                action="pipeline.updated",
                description=f"Pipeline '{p.name}' updated",
                resource_type="pipeline",
                resource_id=str(p.id),
                changes=diff,
            )
        return self._pipeline_response(p)

    async def delete_pipeline(self, pipeline_id: UUID) -> None:
        p = await self._get_pipeline_or_404(pipeline_id)
        name = p.name
        await self.db.delete(p)
        await self.db.flush()
        await self._audit.log(
            action="pipeline.deleted",
            description=f"Pipeline '{name}' deleted",
            resource_type="pipeline",
            resource_id=str(pipeline_id),
        )

    async def add_stage(self, pipeline_id: UUID, data: StageCreate) -> StageResponse:
        await self._get_pipeline_or_404(pipeline_id)
        stage = PipelineStage(
            pipeline_id=pipeline_id,
            name=data.name,
            color=data.color,
            sort_order=data.sort_order,
            is_won=data.is_won,
            is_lost=data.is_lost,
        )
        self.db.add(stage)
        await self.db.flush()
        await self._audit.log(
            action="pipeline.stage_added",
            description=f"Stage '{stage.name}' added",
            resource_type="pipeline_stage",
            resource_id=str(stage.id),
            changes={"pipeline_id": str(pipeline_id), "name": stage.name, "is_won": stage.is_won, "is_lost": stage.is_lost},
        )
        return self._stage_response(stage)

    async def update_stage(self, stage_id: UUID, data: dict) -> StageResponse:
        result = await self.db.execute(select(PipelineStage).where(PipelineStage.id == stage_id))
        stage = result.scalar_one_or_none()
        if not stage:
            raise NotFoundError("Stage not found")
        diff: dict[str, dict] = {}
        for key, value in data.items():
            if value is not None:
                old = getattr(stage, key, None)
                if old != value:
                    diff[key] = {"old": old, "new": value}
                setattr(stage, key, value)
        await self.db.flush()
        if diff:
            await self._audit.log(
                action="pipeline.stage_updated",
                description=f"Stage '{stage.name}' updated",
                resource_type="pipeline_stage",
                resource_id=str(stage.id),
                changes=diff,
            )
        return self._stage_response(stage)

    async def delete_stage(self, stage_id: UUID) -> None:
        result = await self.db.execute(select(PipelineStage).where(PipelineStage.id == stage_id))
        stage = result.scalar_one_or_none()
        if not stage:
            raise NotFoundError("Stage not found")
        name = stage.name
        await self.db.delete(stage)
        await self.db.flush()
        await self._audit.log(
            action="pipeline.stage_deleted",
            description=f"Stage '{name}' deleted",
            resource_type="pipeline_stage",
            resource_id=str(stage_id),
        )

    # ── Deal CRUD ─────────────────────────────────────────────────────────────

    async def list_deals(
        self,
        pipeline_id: UUID,
        *,
        stage_id: UUID | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DealResponse], int]:
        base = select(Deal).where(
            Deal.company_id == self.company_id,
            Deal.pipeline_id == pipeline_id,
            Deal.deleted_at.is_(None),
        )
        if stage_id:
            base = base.where(Deal.stage_id == stage_id)
        if status:
            base = base.where(Deal.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        query = (
            base.options(selectinload(Deal.stage))
            .order_by(Deal.position, Deal.created_at.desc())
            .limit(limit).offset(offset)
        )
        result = await self.db.execute(query)
        deals = result.scalars().unique().all()
        return [self._deal_response(d) for d in deals], total

    async def get_deal(self, deal_id: UUID) -> DealResponse:
        d = await self._get_deal_or_404(deal_id)
        return self._deal_response(d)

    async def create_deal(self, data: DealCreate, user_id: UUID | None = None) -> DealResponse:
        # If no stage, use first stage of pipeline
        stage_id = data.stage_id
        if not stage_id:
            result = await self.db.execute(
                select(PipelineStage)
                .where(PipelineStage.pipeline_id == data.pipeline_id)
                .order_by(PipelineStage.sort_order)
                .limit(1)
            )
            first_stage = result.scalar_one_or_none()
            if first_stage:
                stage_id = first_stage.id

        deal = Deal(
            company_id=self.company_id,
            pipeline_id=data.pipeline_id,
            stage_id=stage_id,
            title=data.title,
            description=data.description,
            value=data.value,
            currency=data.currency,
            contact_id=data.contact_id,
            assigned_to_user_id=data.assigned_to_user_id,
            expected_close_date=data.expected_close_date,
            custom_data=data.custom_data,
        )
        self.db.add(deal)
        await self.db.flush()

        # Log creation (DealActivity = product timeline; AuditLog = compliance trail)
        self.db.add(DealActivity(
            deal_id=deal.id,
            activity_type="created",
            description=f"Deal created: {deal.title}",
            user_id=user_id,
            new_value=str(deal.value),
        ))
        await self.db.flush()
        await self._audit.log(
            action="deal.created",
            description=f"Deal '{deal.title}' created",
            resource_type="deal",
            resource_id=str(deal.id),
            user_id=user_id,
            changes={
                "title": deal.title,
                "value": str(deal.value),
                "currency": deal.currency,
                "pipeline_id": str(deal.pipeline_id),
                "stage_id": str(deal.stage_id) if deal.stage_id else None,
                "contact_id": str(deal.contact_id) if deal.contact_id else None,
            },
        )
        return await self.get_deal(deal.id)

    async def update_deal(
        self, deal_id: UUID, data: DealUpdate, user_id: UUID | None = None
    ) -> DealResponse:
        deal = await self._get_deal_or_404(deal_id)
        update_data = data.model_dump(exclude_unset=True)

        # Track stage change
        if "stage_id" in update_data and update_data["stage_id"] != deal.stage_id:
            old_stage_name = deal.stage.name if deal.stage else "None"
            new_stage = await self.db.execute(
                select(PipelineStage).where(PipelineStage.id == update_data["stage_id"])
            )
            ns = new_stage.scalar_one_or_none()
            new_stage_name = ns.name if ns else "Unknown"

            self.db.add(DealActivity(
                deal_id=deal.id,
                activity_type="stage_changed",
                description=f"Moved from {old_stage_name} to {new_stage_name}",
                user_id=user_id,
                old_value=old_stage_name,
                new_value=new_stage_name,
            ))

        # Track status change
        if "status" in update_data and update_data["status"] != deal.status:
            self.db.add(DealActivity(
                deal_id=deal.id,
                activity_type="status_changed",
                description=f"Status changed to {update_data['status']}",
                user_id=user_id,
                old_value=deal.status,
                new_value=update_data["status"],
            ))
            if update_data["status"] in ("won", "lost"):
                deal.closed_at = datetime.now(timezone.utc)

        # Track value change
        if "value" in update_data and update_data["value"] != deal.value:
            self.db.add(DealActivity(
                deal_id=deal.id,
                activity_type="value_changed",
                description=f"Value changed from {deal.value} to {update_data['value']}",
                user_id=user_id,
                old_value=str(deal.value),
                new_value=str(update_data["value"]),
            ))

        # Build a flat changes dict for audit (separate from DealActivity which
        # is the user-facing timeline).
        diff: dict[str, dict] = {}
        for key, new_value in update_data.items():
            old = getattr(deal, key, None)
            if old != new_value:
                diff[key] = {"old": str(old) if old is not None else None,
                             "new": str(new_value) if new_value is not None else None}
            setattr(deal, key, new_value)

        await self.db.flush()
        if diff:
            await self._audit.log(
                action="deal.updated",
                description=f"Deal '{deal.title}' updated",
                resource_type="deal",
                resource_id=str(deal.id),
                user_id=user_id,
                changes=diff,
            )
        return await self.get_deal(deal_id)

    async def move_deal(
        self, deal_id: UUID, stage_id: UUID, position: int, user_id: UUID | None = None
    ) -> DealResponse:
        """Move a deal to a new stage/position (kanban drag)."""
        return await self.update_deal(
            deal_id,
            DealUpdate(stage_id=stage_id, position=position),
            user_id=user_id,
        )

    async def delete_deal(self, deal_id: UUID) -> None:
        deal = await self._get_deal_or_404(deal_id)
        title = deal.title
        deal.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._audit.log(
            action="deal.deleted",
            description=f"Deal '{title}' soft-deleted",
            resource_type="deal",
            resource_id=str(deal_id),
            changes={"deleted_at": {"old": None, "new": deal.deleted_at.isoformat()}},
        )

    async def get_deal_activities(
        self, deal_id: UUID, limit: int = 50
    ) -> list[DealActivityResponse]:
        result = await self.db.execute(
            select(DealActivity)
            .where(DealActivity.deal_id == deal_id)
            .order_by(DealActivity.created_at.desc())
            .limit(limit)
        )
        return [
            DealActivityResponse(
                id=a.id, deal_id=a.deal_id, activity_type=a.activity_type,
                description=a.description, user_id=a.user_id,
                old_value=a.old_value, new_value=a.new_value,
                created_at=a.created_at,
            )
            for a in result.scalars().all()
        ]

    async def add_note(self, deal_id: UUID, note: str, user_id: UUID | None = None) -> DealActivityResponse:
        deal = await self._get_deal_or_404(deal_id)
        activity = DealActivity(
            deal_id=deal.id,
            activity_type="note_added",
            description=note,
            user_id=user_id,
        )
        self.db.add(activity)
        await self.db.flush()
        return DealActivityResponse(
            id=activity.id, deal_id=activity.deal_id,
            activity_type=activity.activity_type, description=activity.description,
            user_id=activity.user_id, old_value=None, new_value=None,
            created_at=activity.created_at,
        )

    # ── Kanban Board ──────────────────────────────────────────────────────────

    async def get_kanban_board(self, pipeline_id: UUID) -> KanbanBoard:
        pipeline = await self._get_pipeline_or_404(pipeline_id)

        # Get all deals grouped by stage
        deals_result = await self.db.execute(
            select(Deal)
            .where(
                Deal.company_id == self.company_id,
                Deal.pipeline_id == pipeline_id,
                Deal.deleted_at.is_(None),
            )
            .options(selectinload(Deal.stage))
            .order_by(Deal.position, Deal.created_at)
        )
        all_deals = deals_result.scalars().unique().all()

        # Group by stage
        deals_by_stage: dict[UUID, list[Deal]] = {}
        for deal in all_deals:
            sid = deal.stage_id
            if sid not in deals_by_stage:
                deals_by_stage[sid] = []
            deals_by_stage[sid].append(deal)

        columns = []
        for stage in sorted(pipeline.stages, key=lambda s: s.sort_order):
            stage_deals = deals_by_stage.get(stage.id, [])
            total_value = sum(d.value for d in stage_deals)
            columns.append(KanbanColumn(
                stage=self._stage_response(stage),
                deals=[self._deal_response(d) for d in stage_deals],
                total_value=total_value,
                deal_count=len(stage_deals),
            ))

        return KanbanBoard(
            pipeline=self._pipeline_response(pipeline),
            columns=columns,
        )

    # ── Private ───────────────────────────────────────────────────────────────

    async def _get_pipeline_or_404(self, pipeline_id: UUID) -> Pipeline:
        result = await self.db.execute(
            select(Pipeline)
            .where(Pipeline.company_id == self.company_id, Pipeline.id == pipeline_id)
            .options(selectinload(Pipeline.stages))
        )
        p = result.scalar_one_or_none()
        if not p:
            raise NotFoundError("Pipeline not found")
        return p

    async def _get_deal_or_404(self, deal_id: UUID) -> Deal:
        result = await self.db.execute(
            select(Deal)
            .where(
                Deal.company_id == self.company_id,
                Deal.id == deal_id,
                Deal.deleted_at.is_(None),
            )
            .options(selectinload(Deal.stage))
        )
        d = result.scalar_one_or_none()
        if not d:
            raise NotFoundError("Deal not found")
        return d

    def _pipeline_response(self, p: Pipeline) -> PipelineResponse:
        return PipelineResponse(
            id=p.id, name=p.name, description=p.description,
            is_default=p.is_default, is_active=p.is_active,
            stages=[self._stage_response(s) for s in sorted(p.stages, key=lambda s: s.sort_order)],
            created_at=p.created_at, updated_at=p.updated_at,
        )

    def _stage_response(self, s: PipelineStage) -> StageResponse:
        return StageResponse(
            id=s.id, name=s.name, color=s.color,
            sort_order=s.sort_order, is_won=s.is_won, is_lost=s.is_lost,
        )

    def _deal_response(self, d: Deal) -> DealResponse:
        return DealResponse(
            id=d.id, pipeline_id=d.pipeline_id, stage_id=d.stage_id,
            stage=self._stage_response(d.stage) if d.stage else None,
            title=d.title, description=d.description,
            value=d.value, currency=d.currency, status=d.status,
            contact_id=d.contact_id,
            assigned_to_user_id=d.assigned_to_user_id,
            expected_close_date=d.expected_close_date,
            closed_at=d.closed_at, position=d.position,
            custom_data=d.custom_data, company_id=d.company_id,
            created_at=d.created_at, updated_at=d.updated_at,
        )
