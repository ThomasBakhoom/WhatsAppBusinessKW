"""Tag service - CRUD operations for tags."""

from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import ContactTag, Tag
from app.schemas.contacts import TagCreate, TagResponse, TagUpdate
from app.services.actor import Actor
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class TagService:
    def __init__(self, db: AsyncSession, company_id: UUID, actor: Actor | None = None):
        self.db = db
        self.company_id = company_id
        self._audit = AuditService(db, company_id, actor=actor)

    async def list_tags(self) -> list[TagResponse]:
        """List all tags for the company."""
        result = await self.db.execute(
            select(Tag)
            .where(Tag.company_id == self.company_id)
            .order_by(Tag.name)
        )
        tags = result.scalars().all()
        return [self._to_response(t) for t in tags]

    async def get_tag(self, tag_id: UUID) -> TagResponse:
        """Get a single tag."""
        tag = await self._get_tag_or_404(tag_id)
        return self._to_response(tag)

    async def create_tag(self, data: TagCreate) -> TagResponse:
        """Create a new tag."""
        existing = await self.db.execute(
            select(Tag).where(
                Tag.company_id == self.company_id,
                Tag.name == data.name,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Tag '{data.name}' already exists")

        tag = Tag(
            company_id=self.company_id,
            name=data.name,
            color=data.color,
            description=data.description,
        )
        self.db.add(tag)
        await self.db.flush()

        await self._audit.log(
            action="tag.created",
            description=f"Tag '{tag.name}' created",
            resource_type="tag",
            resource_id=str(tag.id),
            changes={"name": tag.name, "color": tag.color, "description": tag.description},
        )

        return self._to_response(tag)

    async def update_tag(self, tag_id: UUID, data: TagUpdate) -> TagResponse:
        """Update a tag."""
        tag = await self._get_tag_or_404(tag_id)

        if data.name and data.name != tag.name:
            existing = await self.db.execute(
                select(Tag).where(
                    Tag.company_id == self.company_id,
                    Tag.name == data.name,
                    Tag.id != tag_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Tag '{data.name}' already exists")

        update_data = data.model_dump(exclude_unset=True)
        diff: dict = {}
        for key, value in update_data.items():
            old_value = getattr(tag, key, None)
            if old_value != value:
                diff[key] = {"old": old_value, "new": value}
            setattr(tag, key, value)

        await self.db.flush()

        if diff:
            await self._audit.log(
                action="tag.updated",
                description=f"Tag '{tag.name}' updated",
                resource_type="tag",
                resource_id=str(tag.id),
                changes=diff,
            )

        return self._to_response(tag)

    async def delete_tag(self, tag_id: UUID) -> None:
        """Delete a tag and all its associations."""
        tag = await self._get_tag_or_404(tag_id)
        tag_name = tag.name
        tag_id_str = str(tag.id)
        await self.db.delete(tag)
        await self.db.flush()

        await self._audit.log(
            action="tag.deleted",
            description=f"Tag '{tag_name}' deleted",
            resource_type="tag",
            resource_id=tag_id_str,
            changes={"name": tag_name},
        )

    async def get_tag_contact_count(self, tag_id: UUID) -> int:
        """Get the number of contacts with this tag."""
        result = await self.db.execute(
            select(func.count()).select_from(ContactTag).where(ContactTag.tag_id == tag_id)
        )
        return result.scalar_one()

    async def _get_tag_or_404(self, tag_id: UUID) -> Tag:
        result = await self.db.execute(
            select(Tag).where(
                Tag.company_id == self.company_id,
                Tag.id == tag_id,
            )
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise NotFoundError("Tag not found")
        return tag

    def _to_response(self, tag: Tag) -> TagResponse:
        return TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            description=tag.description,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )
