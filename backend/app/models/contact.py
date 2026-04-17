"""Contact, Tag, and CustomField models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class Tag(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_tag_company_name"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    contact_tags = relationship("ContactTag", back_populates="tag", lazy="noload")

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


class Contact(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("company_id", "phone", name="uq_contact_company_phone"),
        Index(
            "ix_contact_search",
            "company_id",
            "first_name",
            "last_name",
            "phone",
            "email",
        ),
        Index("ix_contact_company_status", "company_id", "status"),
    )

    # Identity
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    # Profile
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )  # manual, import, whatsapp, landing_page, api

    # Status & Engagement
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, inactive, blocked
    opt_in_whatsapp: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Lead scoring
    lead_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Assigned agent
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships - use noload by default, explicitly selectinload when needed
    tags = relationship("ContactTag", back_populates="contact", lazy="noload", cascade="all, delete-orphan")
    custom_field_values = relationship(
        "CustomFieldValue", back_populates="contact", lazy="noload", cascade="all, delete-orphan"
    )
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], lazy="noload")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.phone

    @property
    def tag_names(self) -> list[str]:
        return [ct.tag.name for ct in self.tags if ct.tag]

    def __repr__(self) -> str:
        return f"<Contact {self.phone}>"


class ContactTag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "contact_tags"
    __table_args__ = (
        UniqueConstraint("contact_id", "tag_id", name="uq_contact_tag"),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    contact = relationship("Contact", back_populates="tags")
    tag = relationship("Tag", back_populates="contact_tags")


class CustomField(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "custom_fields"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_custom_field_company_name"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    field_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )  # text, number, date, select, boolean
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # For select type
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Relationships
    values = relationship("CustomFieldValue", back_populates="custom_field", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CustomField {self.name}>"


class CustomFieldValue(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "custom_field_values"
    __table_args__ = (
        UniqueConstraint("contact_id", "custom_field_id", name="uq_cfv_contact_field"),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    custom_field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custom_fields.id", ondelete="CASCADE"),
        nullable=False,
    )
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    contact = relationship("Contact", back_populates="custom_field_values")
    custom_field = relationship("CustomField", back_populates="values")
