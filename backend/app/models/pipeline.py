"""Pipeline, Stage, Deal, and DealActivity models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class Pipeline(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "pipelines"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    stages = relationship(
        "PipelineStage", back_populates="pipeline", lazy="noload",
        cascade="all, delete-orphan", order_by="PipelineStage.sort_order"
    )

    def __repr__(self) -> str:
        return f"<Pipeline {self.name}>"


class PipelineStage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pipeline_stages"

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_won: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Relationships
    pipeline = relationship("Pipeline", back_populates="stages")
    deals = relationship("Deal", back_populates="stage", lazy="noload")

    def __repr__(self) -> str:
        return f"<Stage {self.name}>"


class Deal(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deal_pipeline_stage", "company_id", "pipeline_id", "stage_id"),
    )

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_stages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Deal info
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=0
    )  # KWD 3 decimals
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KWD")

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open"
    )  # open, won, lost

    # Linked contact
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Assigned agent
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Dates
    expected_close_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Sort within stage (for kanban ordering)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Extra data
    custom_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Relationships
    pipeline = relationship("Pipeline", lazy="noload")
    stage = relationship("PipelineStage", back_populates="deals", lazy="noload")
    contact = relationship("Contact", lazy="noload")
    activities = relationship(
        "DealActivity", back_populates="deal", lazy="noload",
        cascade="all, delete-orphan", order_by="DealActivity.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Deal {self.title}>"


class DealActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "deal_activities"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Activity type: stage_changed, note_added, value_changed, assigned, created, status_changed
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Who did it
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Change details
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    deal = relationship("Deal", back_populates="activities")

    def __repr__(self) -> str:
        return f"<DealActivity {self.activity_type}>"
