"""Glossary API - manage business-specific terms for NLP."""

from uuid import UUID
from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select
from app.dependencies import AuthUser, TenantDbSession
from app.models.glossary import GlossaryTerm
from app.schemas.common import CamelModel, SuccessResponse
from app.core.exceptions import NotFoundError

router = APIRouter()


class GlossaryCreate(CamelModel):
    term: str = Field(..., min_length=1, max_length=200)
    definition: str | None = None
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(default="product", pattern=r"^(product|service|promotion|location|other)$")


class GlossaryResponse(CamelModel):
    id: UUID
    term: str
    definition: str | None
    aliases: list[str]
    category: str
    created_at: str


@router.get("")
async def list_glossary(db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(GlossaryTerm).where(GlossaryTerm.company_id == user.company_id).order_by(GlossaryTerm.term)
    )
    return [GlossaryResponse(id=g.id, term=g.term, definition=g.definition, aliases=g.aliases,
                              category=g.category, created_at=g.created_at.isoformat())
            for g in result.scalars().all()]


@router.post("", response_model=GlossaryResponse, status_code=201)
async def create_glossary_term(data: GlossaryCreate, db: TenantDbSession, user: AuthUser):
    term = GlossaryTerm(company_id=user.company_id, term=data.term, definition=data.definition,
                         aliases=data.aliases, category=data.category)
    db.add(term)
    await db.commit()
    return GlossaryResponse(id=term.id, term=term.term, definition=term.definition,
                             aliases=term.aliases, category=term.category, created_at=term.created_at.isoformat())


@router.delete("/{term_id}", response_model=SuccessResponse)
async def delete_glossary_term(term_id: UUID, db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(GlossaryTerm).where(GlossaryTerm.company_id == user.company_id, GlossaryTerm.id == term_id)
    )
    term = result.scalar_one_or_none()
    if not term:
        raise NotFoundError("Term not found")
    await db.delete(term)
    await db.commit()
    return SuccessResponse(message="Term deleted")
