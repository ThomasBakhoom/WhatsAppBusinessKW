"""Landing page service - CRUD, publish, analytics."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.landing_page import LandingPage
from app.schemas.landing_pages import (
    LandingPageCreate,
    LandingPageListItem,
    LandingPageResponse,
    LandingPageUpdate,
    PageAnalytics,
)

logger = structlog.get_logger()


class LandingPageService:
    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def list_pages(
        self, *, status: str | None = None, limit: int = 20, offset: int = 0
    ) -> tuple[list[LandingPageListItem], int]:
        base = select(LandingPage).where(
            LandingPage.company_id == self.company_id,
            LandingPage.deleted_at.is_(None),
        )
        if status:
            base = base.where(LandingPage.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        query = base.order_by(LandingPage.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        items = [
            LandingPageListItem(
                id=p.id, title=p.title, slug=p.slug, status=p.status,
                visit_count=p.visit_count, conversion_count=p.conversion_count,
                published_at=p.published_at, created_at=p.created_at,
            )
            for p in result.scalars().all()
        ]
        return items, total

    async def get_page(self, page_id: UUID) -> LandingPageResponse:
        p = await self._get_or_404(page_id)
        return self._to_response(p)

    async def get_page_by_slug(self, slug: str) -> LandingPageResponse | None:
        result = await self.db.execute(
            select(LandingPage).where(
                LandingPage.slug == slug,
                LandingPage.status == "published",
                LandingPage.deleted_at.is_(None),
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            return None
        return self._to_response(p)

    async def create_page(self, data: LandingPageCreate) -> LandingPageResponse:
        # Check slug uniqueness
        existing = await self.db.execute(
            select(LandingPage).where(LandingPage.slug == data.slug)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Slug '{data.slug}' already exists")

        page = LandingPage(
            company_id=self.company_id,
            title=data.title,
            slug=data.slug,
            description=data.description,
            blocks=[b.model_dump() for b in data.blocks],
            settings=data.settings,
            whatsapp_number=data.whatsapp_number,
            whatsapp_message=data.whatsapp_message,
            meta_title=data.meta_title,
            meta_description=data.meta_description,
            og_image_url=data.og_image_url,
            template=data.template,
        )
        self.db.add(page)
        await self.db.flush()
        return self._to_response(page)

    async def update_page(self, page_id: UUID, data: LandingPageUpdate) -> LandingPageResponse:
        page = await self._get_or_404(page_id)

        update_data = data.model_dump(exclude_unset=True, exclude={"blocks"})
        for key, value in update_data.items():
            setattr(page, key, value)

        if data.blocks is not None:
            page.blocks = [b.model_dump() for b in data.blocks]

        # Check slug uniqueness if changed
        if data.slug and data.slug != page.slug:
            existing = await self.db.execute(
                select(LandingPage).where(
                    LandingPage.slug == data.slug,
                    LandingPage.id != page_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Slug '{data.slug}' already exists")

        await self.db.flush()
        return self._to_response(page)

    async def publish_page(self, page_id: UUID) -> LandingPageResponse:
        page = await self._get_or_404(page_id)
        page.status = "published"
        page.published_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("landing_page_published", page_id=str(page_id), slug=page.slug)
        return self._to_response(page)

    async def unpublish_page(self, page_id: UUID) -> LandingPageResponse:
        page = await self._get_or_404(page_id)
        page.status = "draft"
        await self.db.flush()
        return self._to_response(page)

    async def delete_page(self, page_id: UUID) -> None:
        page = await self._get_or_404(page_id)
        page.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def record_visit(self, slug: str) -> None:
        await self.db.execute(
            update(LandingPage)
            .where(LandingPage.slug == slug)
            .values(visit_count=LandingPage.visit_count + 1)
        )

    async def record_conversion(self, slug: str) -> None:
        await self.db.execute(
            update(LandingPage)
            .where(LandingPage.slug == slug)
            .values(conversion_count=LandingPage.conversion_count + 1)
        )

    async def get_analytics(self) -> list[PageAnalytics]:
        result = await self.db.execute(
            select(LandingPage).where(
                LandingPage.company_id == self.company_id,
                LandingPage.deleted_at.is_(None),
            ).order_by(LandingPage.visit_count.desc())
        )
        return [
            PageAnalytics(
                page_id=p.id, title=p.title, slug=p.slug,
                visit_count=p.visit_count, conversion_count=p.conversion_count,
                conversion_rate=round(p.conversion_count / max(p.visit_count, 1) * 100, 2),
            )
            for p in result.scalars().all()
        ]

    async def _get_or_404(self, page_id: UUID) -> LandingPage:
        result = await self.db.execute(
            select(LandingPage).where(
                LandingPage.company_id == self.company_id,
                LandingPage.id == page_id,
                LandingPage.deleted_at.is_(None),
            )
        )
        page = result.scalar_one_or_none()
        if not page:
            raise NotFoundError("Landing page not found")
        return page

    def _to_response(self, p: LandingPage) -> LandingPageResponse:
        return LandingPageResponse(
            id=p.id, title=p.title, slug=p.slug, description=p.description,
            status=p.status, published_at=p.published_at,
            blocks=p.blocks, settings=p.settings,
            whatsapp_number=p.whatsapp_number, whatsapp_message=p.whatsapp_message,
            visit_count=p.visit_count, conversion_count=p.conversion_count,
            meta_title=p.meta_title, meta_description=p.meta_description,
            og_image_url=p.og_image_url, template=p.template,
            company_id=p.company_id,
            created_at=p.created_at, updated_at=p.updated_at,
        )
