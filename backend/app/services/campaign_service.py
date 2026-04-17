"""Campaign/Broadcast service."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.campaign import Campaign, CampaignRecipient
from app.models.contact import Contact, ContactTag
from app.schemas.campaigns import CampaignCreate, CampaignResponse, CampaignStats, CampaignUpdate

logger = structlog.get_logger()


class CampaignService:
    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def list_campaigns(self, limit: int = 20, offset: int = 0) -> tuple[list[CampaignResponse], int]:
        base = select(Campaign).where(Campaign.company_id == self.company_id)
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            base.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
        )
        return [self._to_response(c) for c in result.scalars().all()], total

    async def get_campaign(self, campaign_id: UUID) -> CampaignResponse:
        c = await self._get_or_404(campaign_id)
        return self._to_response(c)

    async def create_campaign(self, data: CampaignCreate, user_id: UUID | None = None) -> CampaignResponse:
        campaign = Campaign(
            company_id=self.company_id,
            name=data.name, description=data.description,
            message_type=data.message_type, template_name=data.template_name,
            template_language=data.template_language, message_body=data.message_body,
            media_url=data.media_url, audience_type=data.audience_type,
            audience_filter=data.audience_filter, scheduled_at=data.scheduled_at,
            created_by_user_id=user_id,
        )
        self.db.add(campaign)
        await self.db.flush()
        return self._to_response(campaign)

    async def update_campaign(self, campaign_id: UUID, data: CampaignUpdate) -> CampaignResponse:
        c = await self._get_or_404(campaign_id)
        if c.status not in ("draft", "scheduled"):
            raise ValidationError("Cannot edit a campaign that is already sending")
        for key, val in data.model_dump(exclude_unset=True).items():
            setattr(c, key, val)
        await self.db.flush()
        return self._to_response(c)

    async def delete_campaign(self, campaign_id: UUID) -> None:
        c = await self._get_or_404(campaign_id)
        if c.status == "sending":
            raise ValidationError("Cannot delete a sending campaign")
        await self.db.delete(c)
        await self.db.flush()

    async def send_campaign(self, campaign_id: UUID) -> CampaignResponse:
        """Build recipient list and dispatch to Celery."""
        c = await self._get_or_404(campaign_id)
        if c.status not in ("draft", "scheduled"):
            raise ValidationError(f"Cannot send campaign in status {c.status}")

        # Build audience
        contacts = await self._resolve_audience(c)
        if not contacts:
            raise ValidationError("No contacts match the audience filter")

        # Create recipients
        for contact in contacts:
            self.db.add(CampaignRecipient(
                campaign_id=c.id, contact_id=contact.id, phone=contact.phone,
            ))

        c.status = "sending"
        c.started_at = datetime.now(timezone.utc)
        c.total_recipients = len(contacts)
        await self.db.flush()

        # Dispatch Celery task
        from app.tasks.campaign_tasks import execute_campaign
        execute_campaign.delay(
            campaign_id=str(c.id), company_id=str(self.company_id),
        )

        return self._to_response(c)

    async def pause_campaign(self, campaign_id: UUID) -> CampaignResponse:
        c = await self._get_or_404(campaign_id)
        if c.status != "sending":
            raise ValidationError("Can only pause a sending campaign")
        c.status = "paused"
        await self.db.flush()
        return self._to_response(c)

    async def get_stats(self, campaign_id: UUID) -> CampaignStats:
        c = await self._get_or_404(campaign_id)
        total = max(c.total_recipients, 1)
        return CampaignStats(
            total=c.total_recipients, sent=c.sent_count,
            delivered=c.delivered_count, read=c.read_count, failed=c.failed_count,
            delivery_rate=round(c.delivered_count / total * 100, 1),
            read_rate=round(c.read_count / total * 100, 1),
        )

    async def _resolve_audience(self, campaign: Campaign) -> list[Contact]:
        query = select(Contact).where(
            Contact.company_id == self.company_id,
            Contact.deleted_at.is_(None),
            Contact.opt_in_whatsapp == True,
        )
        af = campaign.audience_filter or {}

        if campaign.audience_type == "tag":
            tag_ids = af.get("tag_ids", [])
            if tag_ids:
                query = query.where(
                    Contact.id.in_(
                        select(ContactTag.contact_id).where(ContactTag.tag_id.in_(tag_ids))
                    )
                )
        if af.get("status"):
            query = query.where(Contact.status == af["status"])
        if af.get("source"):
            query = query.where(Contact.source == af["source"])

        result = await self.db.execute(query.limit(10000))
        return list(result.scalars().all())

    async def _get_or_404(self, campaign_id: UUID) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.company_id == self.company_id, Campaign.id == campaign_id
            )
        )
        c = result.scalar_one_or_none()
        if not c:
            raise NotFoundError("Campaign not found")
        return c

    def _to_response(self, c: Campaign) -> CampaignResponse:
        return CampaignResponse(
            id=c.id, name=c.name, description=c.description, status=c.status,
            message_type=c.message_type, template_name=c.template_name,
            template_language=c.template_language, message_body=c.message_body,
            audience_type=c.audience_type, audience_filter=c.audience_filter,
            scheduled_at=c.scheduled_at, started_at=c.started_at, completed_at=c.completed_at,
            total_recipients=c.total_recipients, sent_count=c.sent_count,
            delivered_count=c.delivered_count, read_count=c.read_count,
            failed_count=c.failed_count, reply_count=c.reply_count,
            created_at=c.created_at, updated_at=c.updated_at,
        )
