"""Custom field service - CRUD operations for custom fields."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import CustomField
from app.schemas.contacts import CustomFieldCreate, CustomFieldResponse, CustomFieldUpdate
from app.services.actor import Actor
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class CustomFieldService:
    def __init__(self, db: AsyncSession, company_id: UUID, actor: Actor | None = None):
        self.db = db
        self.company_id = company_id
        self._audit = AuditService(db, company_id, actor=actor)

    async def list_fields(self) -> list[CustomFieldResponse]:
        """List all custom fields for the company."""
        result = await self.db.execute(
            select(CustomField)
            .where(CustomField.company_id == self.company_id)
            .order_by(CustomField.sort_order, CustomField.name)
        )
        fields = result.scalars().all()
        return [self._to_response(f) for f in fields]

    async def create_field(self, data: CustomFieldCreate) -> CustomFieldResponse:
        """Create a new custom field."""
        existing = await self.db.execute(
            select(CustomField).where(
                CustomField.company_id == self.company_id,
                CustomField.name == data.name,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Custom field '{data.name}' already exists")

        field = CustomField(
            company_id=self.company_id,
            name=data.name,
            label=data.label,
            field_type=data.field_type,
            options=data.options,
            is_required=data.is_required,
            sort_order=data.sort_order,
        )
        self.db.add(field)
        await self.db.flush()

        await self._audit.log(
            action="custom_field.created",
            description=f"Custom field '{field.name}' created",
            resource_type="custom_field",
            resource_id=str(field.id),
            changes={
                "name": field.name, "label": field.label,
                "field_type": field.field_type, "is_required": field.is_required,
            },
        )

        return self._to_response(field)

    async def update_field(self, field_id: UUID, data: CustomFieldUpdate) -> CustomFieldResponse:
        """Update a custom field."""
        field = await self._get_field_or_404(field_id)
        update_data = data.model_dump(exclude_unset=True)
        diff: dict = {}
        for key, value in update_data.items():
            old_value = getattr(field, key, None)
            if old_value != value:
                diff[key] = {"old": old_value, "new": value}
            setattr(field, key, value)
        await self.db.flush()

        if diff:
            await self._audit.log(
                action="custom_field.updated",
                description=f"Custom field '{field.name}' updated",
                resource_type="custom_field",
                resource_id=str(field.id),
                changes=diff,
            )

        return self._to_response(field)

    async def delete_field(self, field_id: UUID) -> None:
        """Delete a custom field and all its values."""
        field = await self._get_field_or_404(field_id)
        field_name = field.name
        field_id_str = str(field.id)
        await self.db.delete(field)
        await self.db.flush()

        await self._audit.log(
            action="custom_field.deleted",
            description=f"Custom field '{field_name}' deleted",
            resource_type="custom_field",
            resource_id=field_id_str,
            changes={"name": field_name},
        )

    async def _get_field_or_404(self, field_id: UUID) -> CustomField:
        result = await self.db.execute(
            select(CustomField).where(
                CustomField.company_id == self.company_id,
                CustomField.id == field_id,
            )
        )
        field = result.scalar_one_or_none()
        if not field:
            raise NotFoundError("Custom field not found")
        return field

    def _to_response(self, field: CustomField) -> CustomFieldResponse:
        return CustomFieldResponse(
            id=field.id,
            name=field.name,
            label=field.label,
            field_type=field.field_type,
            options=field.options,
            is_required=field.is_required,
            sort_order=field.sort_order,
            created_at=field.created_at,
            updated_at=field.updated_at,
        )
