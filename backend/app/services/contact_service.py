"""Contact service - CRUD, search, filter, bulk operations."""

from uuid import UUID

import structlog
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import Contact, ContactTag, CustomField, CustomFieldValue, Tag
from app.schemas.contacts import (
    ContactCreate,
    ContactListItem,
    ContactResponse,
    ContactUpdate,
    CustomFieldValueInput,
    CustomFieldValueResponse,
    TagResponse,
)
from app.services.actor import Actor
from app.services.audit_service import AuditService

logger = structlog.get_logger()


def _jsonable(value):
    """Coerce SQLAlchemy column types into JSON-safe values for audit diffs."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "isoformat"):  # datetime / date
        return value.isoformat()
    if isinstance(value, (str, int, float, bool, list, dict)):
        return value
    return str(value)


class ContactService:
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

    async def list_contacts(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
        source: str | None = None,
        tag_ids: list[UUID] | None = None,
        assigned_to: UUID | None = None,
        sort: str = "-created_at",
    ) -> tuple[list[ContactListItem], int]:
        """List contacts with filtering, search, and pagination."""
        base = select(Contact).where(
            Contact.company_id == self.company_id,
            Contact.deleted_at.is_(None),
        )

        # Filters
        if status:
            base = base.where(Contact.status == status)
        if source:
            base = base.where(Contact.source == source)
        if assigned_to:
            base = base.where(Contact.assigned_to_user_id == assigned_to)

        # Search across name, phone, email
        if search:
            term = f"%{search}%"
            base = base.where(
                or_(
                    Contact.first_name.ilike(term),
                    Contact.last_name.ilike(term),
                    Contact.phone.ilike(term),
                    Contact.email.ilike(term),
                )
            )

        # Tag filter - contacts that have ALL specified tags
        if tag_ids:
            for tag_id in tag_ids:
                base = base.where(
                    Contact.id.in_(
                        select(ContactTag.contact_id).where(ContactTag.tag_id == tag_id)
                    )
                )

        # Count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Sort
        sort_field = sort.lstrip("-+")
        descending = sort.startswith("-")
        col = getattr(Contact, sort_field, Contact.created_at)
        order = col.desc() if descending else col.asc()

        # Query with eager loading
        query = (
            base.options(selectinload(Contact.tags).selectinload(ContactTag.tag))
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        contacts = result.scalars().unique().all()

        items = [self._to_list_item(c) for c in contacts]
        return items, total

    async def get_contact(self, contact_id: UUID) -> ContactResponse:
        """Get a single contact with full details."""
        contact = await self._get_contact_or_404(contact_id)
        return self._to_response(contact)

    async def create_contact(self, data: ContactCreate) -> ContactResponse:
        """Create a new contact."""
        # Check phone uniqueness within company
        existing = await self.db.execute(
            select(Contact).where(
                Contact.company_id == self.company_id,
                Contact.phone == data.phone,
                Contact.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Contact with phone '{data.phone}' already exists")

        contact = Contact(
            company_id=self.company_id,
            phone=data.phone,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            notes=data.notes,
            source=data.source,
            status=data.status,
            opt_in_whatsapp=data.opt_in_whatsapp,
            assigned_to_user_id=data.assigned_to_user_id,
        )
        self.db.add(contact)
        await self.db.flush()

        # Add tags
        if data.tag_ids:
            await self._set_tags(contact, data.tag_ids)

        # Add custom field values
        if data.custom_fields:
            await self._set_custom_field_values(contact, data.custom_fields)

        await self.db.flush()

        await self._audit.log(
            action="contact.created",
            description=f"Contact {contact.full_name or contact.phone} created",
            resource_type="contact",
            resource_id=str(contact.id),
            changes={
                "phone": contact.phone,
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "source": contact.source,
                "status": contact.status,
                "tag_ids": [str(t) for t in (data.tag_ids or [])],
            },
        )

        # Reload with relationships
        return await self.get_contact(contact.id)

    async def update_contact(self, contact_id: UUID, data: ContactUpdate) -> ContactResponse:
        """Update a contact."""
        contact = await self._get_contact_or_404(contact_id)

        # Check phone uniqueness if changing phone
        if data.phone and data.phone != contact.phone:
            existing = await self.db.execute(
                select(Contact).where(
                    Contact.company_id == self.company_id,
                    Contact.phone == data.phone,
                    Contact.deleted_at.is_(None),
                    Contact.id != contact_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Contact with phone '{data.phone}' already exists")

        # Compute the changes diff BEFORE applying so we can record old/new pairs.
        update_data = data.model_dump(exclude_unset=True, exclude={"tag_ids", "custom_fields"})
        diff: dict[str, dict] = {}
        for key, new_value in update_data.items():
            old_value = getattr(contact, key, None)
            if old_value != new_value:
                diff[key] = {"old": _jsonable(old_value), "new": _jsonable(new_value)}
            setattr(contact, key, new_value)

        # Update tags if provided
        if data.tag_ids is not None:
            await self._set_tags(contact, data.tag_ids)
            diff["tag_ids"] = {"new": [str(t) for t in data.tag_ids]}

        # Update custom fields if provided
        if data.custom_fields is not None:
            await self._set_custom_field_values(contact, data.custom_fields)
            diff["custom_fields"] = {"new": [
                {"id": str(f.custom_field_id), "value": f.value}
                for f in data.custom_fields
            ]}

        await self.db.flush()

        if diff:
            await self._audit.log(
                action="contact.updated",
                description=f"Contact {contact.full_name or contact.phone} updated",
                resource_type="contact",
                resource_id=str(contact.id),
                changes=diff,
            )

        return await self.get_contact(contact_id)

    async def delete_contact(self, contact_id: UUID) -> None:
        """Soft-delete a contact."""
        contact = await self._get_contact_or_404(contact_id)
        from datetime import datetime, timezone
        contact.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._audit.log(
            action="contact.deleted",
            description=f"Contact {contact.full_name or contact.phone} soft-deleted",
            resource_type="contact",
            resource_id=str(contact.id),
            changes={"deleted_at": {"old": None, "new": contact.deleted_at.isoformat()}},
        )

    async def bulk_action(
        self,
        contact_ids: list[UUID],
        action: str,
        *,
        tag_id: UUID | None = None,
        status: str | None = None,
        assigned_to_user_id: UUID | None = None,
    ) -> int:
        """Execute a bulk action on multiple contacts. Returns affected count."""
        contacts_q = await self.db.execute(
            select(Contact)
            .where(
                Contact.company_id == self.company_id,
                Contact.id.in_(contact_ids),
                Contact.deleted_at.is_(None),
            )
            .options(selectinload(Contact.tags))
        )
        contacts = contacts_q.scalars().unique().all()

        if action == "delete":
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            for c in contacts:
                c.deleted_at = now
        elif action == "add_tag" and tag_id:
            for c in contacts:
                existing_tag_ids = {ct.tag_id for ct in c.tags}
                if tag_id not in existing_tag_ids:
                    self.db.add(ContactTag(contact_id=c.id, tag_id=tag_id))
        elif action == "remove_tag" and tag_id:
            await self.db.execute(
                delete(ContactTag).where(
                    ContactTag.contact_id.in_(contact_ids),
                    ContactTag.tag_id == tag_id,
                )
            )
        elif action == "change_status" and status:
            for c in contacts:
                c.status = status
        elif action == "assign":
            for c in contacts:
                c.assigned_to_user_id = assigned_to_user_id

        await self.db.flush()

        if contacts:
            await self._audit.log(
                action=f"contact.bulk_{action}",
                description=f"Bulk {action} on {len(contacts)} contact(s)",
                resource_type="contact",
                resource_id=None,
                changes={
                    "action": action,
                    "contact_ids": [str(c.id) for c in contacts],
                    "tag_id": str(tag_id) if tag_id else None,
                    "status": status,
                    "assigned_to_user_id": str(assigned_to_user_id) if assigned_to_user_id else None,
                },
            )

        return len(contacts)

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _get_contact_or_404(self, contact_id: UUID) -> Contact:
        result = await self.db.execute(
            select(Contact)
            .where(
                Contact.company_id == self.company_id,
                Contact.id == contact_id,
                Contact.deleted_at.is_(None),
            )
            .options(
                selectinload(Contact.tags).selectinload(ContactTag.tag),
                selectinload(Contact.custom_field_values).selectinload(
                    CustomFieldValue.custom_field
                ),
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("Contact not found")
        return contact

    async def _set_tags(self, contact: Contact, tag_ids: list[UUID]) -> None:
        """Replace all tags on a contact."""
        await self.db.execute(
            delete(ContactTag).where(ContactTag.contact_id == contact.id)
        )
        for tag_id in tag_ids:
            self.db.add(ContactTag(contact_id=contact.id, tag_id=tag_id))

    async def _set_custom_field_values(
        self, contact: Contact, fields: list[CustomFieldValueInput]
    ) -> None:
        """Replace custom field values on a contact."""
        await self.db.execute(
            delete(CustomFieldValue).where(CustomFieldValue.contact_id == contact.id)
        )
        for fv in fields:
            self.db.add(
                CustomFieldValue(
                    contact_id=contact.id,
                    custom_field_id=fv.custom_field_id,
                    value=fv.value,
                )
            )

    def _to_response(self, contact: Contact) -> ContactResponse:
        return ContactResponse(
            id=contact.id,
            phone=contact.phone,
            email=contact.email,
            first_name=contact.first_name,
            last_name=contact.last_name,
            full_name=contact.full_name,
            avatar_url=contact.avatar_url,
            notes=contact.notes,
            source=contact.source,
            status=contact.status,
            opt_in_whatsapp=contact.opt_in_whatsapp,
            lead_score=contact.lead_score,
            last_contacted_at=contact.last_contacted_at,
            assigned_to_user_id=contact.assigned_to_user_id,
            tags=[
                TagResponse(
                    id=ct.tag.id,
                    name=ct.tag.name,
                    color=ct.tag.color,
                    description=ct.tag.description,
                    created_at=ct.tag.created_at,
                    updated_at=ct.tag.updated_at,
                )
                for ct in contact.tags
                if ct.tag
            ],
            custom_fields=[
                CustomFieldValueResponse(
                    custom_field_id=cfv.custom_field.id,
                    field_name=cfv.custom_field.name,
                    field_label=cfv.custom_field.label,
                    field_type=cfv.custom_field.field_type,
                    value=cfv.value,
                )
                for cfv in contact.custom_field_values
                if cfv.custom_field
            ],
            company_id=contact.company_id,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )

    def _to_list_item(self, contact: Contact) -> ContactListItem:
        return ContactListItem(
            id=contact.id,
            phone=contact.phone,
            email=contact.email,
            first_name=contact.first_name,
            last_name=contact.last_name,
            full_name=contact.full_name,
            status=contact.status,
            source=contact.source,
            lead_score=contact.lead_score,
            opt_in_whatsapp=contact.opt_in_whatsapp,
            last_contacted_at=contact.last_contacted_at,
            assigned_to_user_id=contact.assigned_to_user_id,
            tags=[
                TagResponse(
                    id=ct.tag.id,
                    name=ct.tag.name,
                    color=ct.tag.color,
                    description=ct.tag.description,
                    created_at=ct.tag.created_at,
                    updated_at=ct.tag.updated_at,
                )
                for ct in contact.tags
                if ct.tag
            ],
            created_at=contact.created_at,
        )
