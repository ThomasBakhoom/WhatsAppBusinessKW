"""Analytics service - dashboard stats, message metrics, pipeline, team performance."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import and_, case, cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import Automation, AutomationLog
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.landing_page import LandingPage
from app.models.message import Message
from app.models.pipeline import Deal, Pipeline, PipelineStage

logger = structlog.get_logger()


class AnalyticsService:
    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def get_dashboard(self, days: int = 30) -> dict:
        """Top-level dashboard with summary stats."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        contacts_total = await self._count(Contact, Contact.deleted_at.is_(None))
        contacts_new = await self._count(Contact, Contact.created_at >= since, Contact.deleted_at.is_(None))

        convs_total = await self._count(Conversation)
        convs_open = await self._count(Conversation, Conversation.status == "open")

        msgs_total = await self._count(Message)
        msgs_inbound = await self._count(Message, Message.direction == "inbound", Message.created_at >= since)
        msgs_outbound = await self._count(Message, Message.direction == "outbound", Message.created_at >= since)

        deals_result = await self.db.execute(
            select(func.count(), func.coalesce(func.sum(Deal.value), 0)).where(
                Deal.company_id == self.company_id,
                Deal.status == "won",
                Deal.deleted_at.is_(None),
            )
        )
        won_row = deals_result.one()
        deals_won = won_row[0]
        revenue = won_row[1]

        pipeline_value = await self.db.execute(
            select(func.coalesce(func.sum(Deal.value), 0)).where(
                Deal.company_id == self.company_id,
                Deal.status == "open",
                Deal.deleted_at.is_(None),
            )
        )
        open_pipeline = pipeline_value.scalar_one()

        return {
            "period_days": days,
            "contacts": {"total": contacts_total, "new": contacts_new},
            "conversations": {"total": convs_total, "open": convs_open},
            "messages": {"total": msgs_total, "inbound": msgs_inbound, "outbound": msgs_outbound},
            "deals": {"won": deals_won, "revenue": float(revenue), "open_pipeline_value": float(open_pipeline)},
        }

    async def get_message_stats(self, days: int = 30) -> dict:
        """Message volume over time."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                cast(Message.created_at, Date).label("date"),
                Message.direction,
                func.count().label("count"),
            )
            .where(Message.company_id == self.company_id, Message.created_at >= since)
            .group_by("date", Message.direction)
            .order_by("date")
        )

        daily = {}
        for row in result.all():
            d = str(row.date)
            if d not in daily:
                daily[d] = {"date": d, "inbound": 0, "outbound": 0}
            daily[d][row.direction] = row.count

        # Delivery stats
        delivery = await self.db.execute(
            select(Message.delivery_status, func.count()).where(
                Message.company_id == self.company_id,
                Message.direction == "outbound",
                Message.created_at >= since,
            ).group_by(Message.delivery_status)
        )
        delivery_stats = {row[0]: row[1] for row in delivery.all()}

        return {
            "daily": list(daily.values()),
            "delivery_stats": delivery_stats,
        }

    async def get_pipeline_stats(self) -> dict:
        """Pipeline analytics - deal value by stage, win rate."""
        result = await self.db.execute(
            select(Pipeline).where(Pipeline.company_id == self.company_id).limit(1)
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            return {"stages": [], "win_rate": 0, "avg_deal_value": 0}

        stages_result = await self.db.execute(
            select(
                PipelineStage.name,
                PipelineStage.color,
                func.count(Deal.id).label("deal_count"),
                func.coalesce(func.sum(Deal.value), 0).label("total_value"),
            )
            .outerjoin(Deal, and_(Deal.stage_id == PipelineStage.id, Deal.deleted_at.is_(None)))
            .where(PipelineStage.pipeline_id == pipeline.id)
            .group_by(PipelineStage.id)
            .order_by(PipelineStage.sort_order)
        )

        stages = [
            {"name": r.name, "color": r.color, "deal_count": r.deal_count, "total_value": float(r.total_value)}
            for r in stages_result.all()
        ]

        # Win rate
        total_closed = await self._count(Deal, Deal.status.in_(["won", "lost"]), Deal.deleted_at.is_(None))
        won = await self._count(Deal, Deal.status == "won", Deal.deleted_at.is_(None))
        win_rate = round(won / max(total_closed, 1) * 100, 1)

        # Avg deal value
        avg_result = await self.db.execute(
            select(func.coalesce(func.avg(Deal.value), 0)).where(
                Deal.company_id == self.company_id, Deal.status == "won", Deal.deleted_at.is_(None)
            )
        )
        avg_deal = float(avg_result.scalar_one())

        return {"stages": stages, "win_rate": win_rate, "avg_deal_value": avg_deal}

    async def get_team_stats(self, days: int = 30) -> list[dict]:
        """Per-agent performance stats."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        from app.models.auth import User

        agents = await self.db.execute(
            select(User).where(User.company_id == self.company_id, User.is_active == True)
        )

        stats = []
        for agent in agents.scalars().all():
            msgs_sent = await self.db.execute(
                select(func.count()).select_from(Message).where(
                    Message.company_id == self.company_id,
                    Message.sender_id == agent.id,
                    Message.created_at >= since,
                )
            )
            convs_assigned = await self.db.execute(
                select(func.count()).select_from(Conversation).where(
                    Conversation.company_id == self.company_id,
                    Conversation.assigned_to_user_id == agent.id,
                )
            )
            deals_won = await self.db.execute(
                select(func.count(), func.coalesce(func.sum(Deal.value), 0)).where(
                    Deal.company_id == self.company_id,
                    Deal.assigned_to_user_id == agent.id,
                    Deal.status == "won",
                    Deal.deleted_at.is_(None),
                )
            )
            dw = deals_won.one()

            stats.append({
                "user_id": str(agent.id),
                "name": agent.full_name,
                "email": agent.email,
                "is_online": agent.is_online,
                "messages_sent": msgs_sent.scalar_one(),
                "conversations_assigned": convs_assigned.scalar_one(),
                "deals_won": dw[0],
                "revenue": float(dw[1]),
            })

        return sorted(stats, key=lambda x: x["revenue"], reverse=True)

    async def get_landing_page_stats(self) -> list[dict]:
        """Landing page performance."""
        result = await self.db.execute(
            select(LandingPage).where(
                LandingPage.company_id == self.company_id,
                LandingPage.deleted_at.is_(None),
            ).order_by(LandingPage.visit_count.desc())
        )
        return [
            {
                "id": str(p.id), "title": p.title, "slug": p.slug, "status": p.status,
                "visits": p.visit_count, "conversions": p.conversion_count,
                "rate": round(p.conversion_count / max(p.visit_count, 1) * 100, 1),
            }
            for p in result.scalars().all()
        ]

    async def get_automation_stats(self) -> dict:
        """Automation execution stats."""
        total = await self._count(Automation)
        active = await self._count(Automation, Automation.is_active == True)

        exec_result = await self.db.execute(
            select(
                AutomationLog.status,
                func.count(),
            ).where(AutomationLog.company_id == self.company_id)
            .group_by(AutomationLog.status)
        )
        exec_stats = {r[0]: r[1] for r in exec_result.all()}

        return {
            "total": total, "active": active,
            "executions": exec_stats,
        }

    async def _count(self, model, *filters) -> int:
        q = select(func.count()).select_from(model).where(
            model.company_id == self.company_id, *filters
        )
        return (await self.db.execute(q)).scalar_one()
