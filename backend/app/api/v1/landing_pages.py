"""Landing page API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.pagination import PaginatedResponse
from app.dependencies import AuthUser, DbSession, TenantDbSession
from app.schemas.common import SuccessResponse
from app.schemas.landing_pages import (
    LandingPageCreate,
    LandingPageListItem,
    LandingPageResponse,
    LandingPageUpdate,
    PageAnalytics,
)
from app.services.landing_page_service import LandingPageService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LandingPageListItem])
async def list_pages(
    db: TenantDbSession,
    user: AuthUser,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    svc = LandingPageService(db, user.company_id)
    items, total = await svc.list_pages(status=status, limit=limit, offset=offset)
    return PaginatedResponse.create(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=LandingPageResponse, status_code=201)
async def create_page(data: LandingPageCreate, db: TenantDbSession, user: AuthUser):
    svc = LandingPageService(db, user.company_id)
    page = await svc.create_page(data)
    await db.commit()
    return page


@router.get("/{page_id}", response_model=LandingPageResponse)
async def get_page(page_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = LandingPageService(db, user.company_id)
    return await svc.get_page(page_id)


@router.patch("/{page_id}", response_model=LandingPageResponse)
async def update_page(page_id: UUID, data: LandingPageUpdate, db: TenantDbSession, user: AuthUser):
    svc = LandingPageService(db, user.company_id)
    page = await svc.update_page(page_id, data)
    await db.commit()
    return page


@router.post("/{page_id}/publish", response_model=LandingPageResponse)
async def publish_page(page_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = LandingPageService(db, user.company_id)
    page = await svc.publish_page(page_id)
    await db.commit()
    return page


@router.post("/{page_id}/unpublish", response_model=LandingPageResponse)
async def unpublish_page(page_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = LandingPageService(db, user.company_id)
    page = await svc.unpublish_page(page_id)
    await db.commit()
    return page


@router.delete("/{page_id}", response_model=SuccessResponse)
async def delete_page(page_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = LandingPageService(db, user.company_id)
    await svc.delete_page(page_id)
    await db.commit()
    return SuccessResponse(message="Landing page deleted")


@router.get("/analytics/all", response_model=list[PageAnalytics])
async def get_page_analytics(db: TenantDbSession, user: AuthUser):
    svc = LandingPageService(db, user.company_id)
    return await svc.get_analytics()


# ── Public endpoint (no auth) ────────────────────────────────────────────────

@router.get("/public/{slug}", response_model=LandingPageResponse)
async def get_public_page(slug: str, db: DbSession):
    """Public endpoint to fetch a published landing page by slug."""
    from sqlalchemy import select, update
    from app.models.landing_page import LandingPage

    result = await db.execute(
        select(LandingPage).where(
            LandingPage.slug == slug,
            LandingPage.status == "published",
            LandingPage.deleted_at.is_(None),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Page not found")

    # Capture values before expunging to avoid dirty-tracking flush issues
    # under RLS (public session has no tenant context for writes).
    response = LandingPageResponse(
        id=page.id, title=page.title, slug=page.slug, description=page.description,
        status=page.status, published_at=page.published_at,
        blocks=page.blocks, settings=page.settings,
        whatsapp_number=page.whatsapp_number, whatsapp_message=page.whatsapp_message,
        visit_count=(page.visit_count or 0) + 1,
        conversion_count=page.conversion_count,
        meta_title=page.meta_title, meta_description=page.meta_description,
        og_image_url=page.og_image_url, template=page.template,
        company_id=page.company_id,
        created_at=page.created_at, updated_at=page.updated_at,
    )
    db.expunge(page)

    # Record visit via core UPDATE (best-effort; may be blocked by RLS)
    await db.execute(
        update(LandingPage)
        .where(LandingPage.id == response.id)
        .values(visit_count=response.visit_count)
    )

    return response


@router.post("/public/{slug}/convert")
async def record_conversion(slug: str, db: DbSession):
    """Record a WhatsApp CTA click conversion."""
    from sqlalchemy import select, update
    from app.models.landing_page import LandingPage

    await db.execute(
        update(LandingPage)
        .where(LandingPage.slug == slug, LandingPage.status == "published")
        .values(conversion_count=LandingPage.conversion_count + 1)
    )
    return {"status": "ok"}
