"""Automation models - triggers, conditions, actions, and logs."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Automation(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """An automation rule with trigger, conditions, and actions."""

    __tablename__ = "automations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Trigger: the event that starts this automation
    # e.g., "message.received", "contact.created", "deal.stage_changed"
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)

    # Conditions: JSON array of conditions that must all be true
    # e.g., [{"field": "message.content", "operator": "contains", "value": "price"}]
    conditions: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    # Priority for ordering when multiple automations match
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Stats
    execution_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    actions = relationship(
        "AutomationAction", back_populates="automation", lazy="noload",
        cascade="all, delete-orphan", order_by="AutomationAction.sort_order"
    )
    logs = relationship(
        "AutomationLog", back_populates="automation", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Automation {self.name}>"


class AutomationAction(Base, UUIDMixin, TimestampMixin):
    """A single action to execute when an automation fires."""

    __tablename__ = "automation_actions"

    automation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Action type: send_message, assign_agent, add_tag, remove_tag,
    # change_status, update_lead_score, send_template, webhook
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Action configuration (type-specific)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Relationships
    automation = relationship("Automation", back_populates="actions")

    def __repr__(self) -> str:
        return f"<AutomationAction {self.action_type}>"


class AutomationLog(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Execution log for an automation run."""

    __tablename__ = "automation_logs"

    automation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # What triggered it
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Result
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success"
    )  # success, failed, skipped
    actions_executed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    automation = relationship("Automation", back_populates="logs")

    def __repr__(self) -> str:
        return f"<AutomationLog {self.automation_id} {self.status}>"
