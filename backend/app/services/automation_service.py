"""Automation service - CRUD and rule evaluation engine."""

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.automation import Automation, AutomationAction, AutomationLog
from app.schemas.automations import (
    AutomationCreate,
    AutomationResponse,
    AutomationUpdate,
    AutomationActionResponse,
    AutomationLogResponse,
)

logger = structlog.get_logger()


class AutomationService:
    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def list_automations(self) -> list[AutomationResponse]:
        result = await self.db.execute(
            select(Automation)
            .where(Automation.company_id == self.company_id)
            .options(selectinload(Automation.actions))
            .order_by(Automation.priority.desc(), Automation.name)
        )
        return [self._to_response(a) for a in result.scalars().unique().all()]

    async def get_automation(self, automation_id: UUID) -> AutomationResponse:
        auto = await self._get_or_404(automation_id)
        return self._to_response(auto)

    async def create_automation(self, data: AutomationCreate) -> AutomationResponse:
        auto = Automation(
            company_id=self.company_id,
            name=data.name,
            description=data.description,
            trigger_event=data.trigger_event,
            conditions=[c.model_dump() for c in data.conditions],
            priority=data.priority,
            is_active=data.is_active,
        )
        self.db.add(auto)
        await self.db.flush()

        for action_data in data.actions:
            action = AutomationAction(
                automation_id=auto.id,
                action_type=action_data.action_type,
                config=action_data.config,
                sort_order=action_data.sort_order,
            )
            self.db.add(action)

        await self.db.flush()
        return await self.get_automation(auto.id)

    async def update_automation(
        self, automation_id: UUID, data: AutomationUpdate
    ) -> AutomationResponse:
        auto = await self._get_or_404(automation_id)

        update_data = data.model_dump(exclude_unset=True, exclude={"actions", "conditions"})
        for key, value in update_data.items():
            setattr(auto, key, value)

        if data.conditions is not None:
            auto.conditions = [c.model_dump() for c in data.conditions]

        if data.actions is not None:
            await self.db.execute(
                delete(AutomationAction).where(
                    AutomationAction.automation_id == automation_id
                )
            )
            for action_data in data.actions:
                action = AutomationAction(
                    automation_id=automation_id,
                    action_type=action_data.action_type,
                    config=action_data.config,
                    sort_order=action_data.sort_order,
                )
                self.db.add(action)

        await self.db.flush()
        return await self.get_automation(automation_id)

    async def delete_automation(self, automation_id: UUID) -> None:
        auto = await self._get_or_404(automation_id)
        await self.db.delete(auto)
        await self.db.flush()

    async def toggle_automation(self, automation_id: UUID) -> AutomationResponse:
        auto = await self._get_or_404(automation_id)
        auto.is_active = not auto.is_active
        await self.db.flush()
        return self._to_response(auto)

    async def get_logs(
        self, automation_id: UUID, limit: int = 50
    ) -> list[AutomationLogResponse]:
        result = await self.db.execute(
            select(AutomationLog)
            .where(AutomationLog.automation_id == automation_id)
            .order_by(AutomationLog.created_at.desc())
            .limit(limit)
        )
        return [
            AutomationLogResponse(
                id=log.id,
                automation_id=log.automation_id,
                trigger_event=log.trigger_event,
                trigger_data=log.trigger_data,
                status=log.status,
                actions_executed=log.actions_executed,
                error_message=log.error_message,
                duration_ms=log.duration_ms,
                created_at=log.created_at,
            )
            for log in result.scalars().all()
        ]

    # ── Rule Evaluation Engine ────────────────────────────────────────────────

    async def evaluate_event(
        self, event_type: str, event_data: dict[str, Any]
    ) -> list[UUID]:
        """
        Evaluate all active automations for a given event.
        Returns list of automation IDs that were executed.
        """
        result = await self.db.execute(
            select(Automation)
            .where(
                Automation.company_id == self.company_id,
                Automation.is_active == True,
                Automation.trigger_event == event_type,
            )
            .options(selectinload(Automation.actions))
            .order_by(Automation.priority.desc())
        )
        automations = result.scalars().unique().all()

        executed_ids = []
        for auto in automations:
            if self._check_conditions(auto.conditions, event_data):
                await self._execute_automation(auto, event_type, event_data)
                executed_ids.append(auto.id)

        return executed_ids

    def _check_conditions(
        self, conditions: list[dict], event_data: dict[str, Any]
    ) -> bool:
        """Check if all conditions are met."""
        if not conditions:
            return True

        for condition in conditions:
            field_path = condition.get("field", "")
            operator = condition.get("operator", "equals")
            expected = condition.get("value")

            actual = self._resolve_field(field_path, event_data)

            if not self._evaluate_condition(actual, operator, expected):
                return False

        return True

    def _resolve_field(self, field_path: str, data: dict) -> Any:
        """Resolve a dotted field path from event data."""
        parts = field_path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a single condition."""
        if actual is None and operator != "not_equals":
            return False

        if operator == "equals":
            return str(actual).lower() == str(expected).lower()
        elif operator == "not_equals":
            return str(actual).lower() != str(expected).lower()
        elif operator == "contains":
            return str(expected).lower() in str(actual).lower()
        elif operator == "starts_with":
            return str(actual).lower().startswith(str(expected).lower())
        elif operator == "gt":
            return float(actual) > float(expected)
        elif operator == "lt":
            return float(actual) < float(expected)
        elif operator == "in":
            if isinstance(expected, list):
                return actual in expected
            return str(actual) in str(expected).split(",")
        else:
            return False

    async def _execute_automation(
        self, auto: Automation, event_type: str, event_data: dict
    ):
        """Execute all actions for an automation."""
        start = time.monotonic()
        actions_executed = 0
        error_message = None
        status = "success"

        try:
            for action in sorted(auto.actions, key=lambda a: a.sort_order):
                await self._execute_action(action, event_data)
                actions_executed += 1
        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(
                "automation_action_failed",
                automation_id=str(auto.id),
                error=str(e),
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        # Update automation stats
        auto.execution_count = (auto.execution_count or 0) + 1
        auto.last_executed_at = datetime.now(timezone.utc)

        # Write log
        log = AutomationLog(
            company_id=self.company_id,
            automation_id=auto.id,
            trigger_event=event_type,
            trigger_data=event_data,
            status=status,
            actions_executed=actions_executed,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.db.add(log)
        await self.db.flush()

        logger.info(
            "automation_executed",
            automation_id=str(auto.id),
            name=auto.name,
            status=status,
            actions=actions_executed,
            duration_ms=duration_ms,
        )

    async def _execute_action(
        self, action: AutomationAction, event_data: dict
    ):
        """Execute a single automation action."""
        config = action.config

        if action.action_type == "add_tag":
            await self._action_add_tag(config, event_data)
        elif action.action_type == "remove_tag":
            await self._action_remove_tag(config, event_data)
        elif action.action_type == "change_status":
            await self._action_change_status(config, event_data)
        elif action.action_type == "update_lead_score":
            await self._action_update_lead_score(config, event_data)
        elif action.action_type == "assign_agent":
            await self._action_assign_agent(config, event_data)
        elif action.action_type == "auto_reply":
            await self._action_auto_reply(config, event_data)
        elif action.action_type == "send_template":
            await self._action_send_template(config, event_data)
        else:
            logger.warning("unknown_action_type", action_type=action.action_type)

    async def _action_add_tag(self, config: dict, event_data: dict):
        from app.models.contact import Contact, ContactTag
        contact_id = event_data.get("contact_id")
        tag_id = config.get("tag_id")
        if contact_id and tag_id:
            existing = await self.db.execute(
                select(ContactTag).where(
                    ContactTag.contact_id == UUID(contact_id),
                    ContactTag.tag_id == UUID(tag_id),
                )
            )
            if not existing.scalar_one_or_none():
                self.db.add(ContactTag(
                    contact_id=UUID(contact_id), tag_id=UUID(tag_id)
                ))

    async def _action_remove_tag(self, config: dict, event_data: dict):
        from app.models.contact import ContactTag
        contact_id = event_data.get("contact_id")
        tag_id = config.get("tag_id")
        if contact_id and tag_id:
            await self.db.execute(
                delete(ContactTag).where(
                    ContactTag.contact_id == UUID(contact_id),
                    ContactTag.tag_id == UUID(tag_id),
                )
            )

    async def _action_change_status(self, config: dict, event_data: dict):
        from app.models.contact import Contact
        contact_id = event_data.get("contact_id")
        new_status = config.get("status")
        if contact_id and new_status:
            await self.db.execute(
                update(Contact)
                .where(Contact.id == UUID(contact_id))
                .values(status=new_status)
            )

    async def _action_update_lead_score(self, config: dict, event_data: dict):
        from app.models.contact import Contact
        contact_id = event_data.get("contact_id")
        delta = config.get("delta", 0)
        if contact_id:
            await self.db.execute(
                update(Contact)
                .where(Contact.id == UUID(contact_id))
                .values(lead_score=Contact.lead_score + int(delta))
            )

    async def _action_assign_agent(self, config: dict, event_data: dict):
        from app.models.conversation import Conversation
        conversation_id = event_data.get("conversation_id")
        if conversation_id:
            # Use routing engine or specific agent
            agent_id = config.get("agent_id")
            if agent_id:
                await self.db.execute(
                    update(Conversation)
                    .where(Conversation.id == UUID(conversation_id))
                    .values(assigned_to_user_id=UUID(agent_id))
                )
            else:
                # Use smart routing
                from app.services.routing_engine import RoutingEngine
                conv_result = await self.db.execute(
                    select(Conversation).where(Conversation.id == UUID(conversation_id))
                )
                conv = conv_result.scalar_one_or_none()
                if conv:
                    router = RoutingEngine(self.db, self.company_id)
                    best = await router.assign_conversation(
                        conv,
                        preferred_skills=config.get("skills"),
                        language=config.get("language"),
                    )
                    if best:
                        conv.assigned_to_user_id = best

    async def _action_auto_reply(self, config: dict, event_data: dict):
        """Queue an auto-reply message."""
        conversation_id = event_data.get("conversation_id")
        message_text = config.get("message")
        if conversation_id and message_text:
            from app.services.conversation_service import ConversationService
            svc = ConversationService(self.db, self.company_id)
            await svc.add_message(
                UUID(conversation_id),
                direction="outbound",
                sender_type="bot",
                message_type="text",
                content=message_text,
                delivery_status="pending",
            )

    async def _action_send_template(self, config: dict, event_data: dict):
        """Queue a template message send."""
        conversation_id = event_data.get("conversation_id")
        template_name = config.get("template_name")
        if conversation_id and template_name:
            from app.services.conversation_service import ConversationService
            svc = ConversationService(self.db, self.company_id)
            await svc.add_message(
                UUID(conversation_id),
                direction="outbound",
                sender_type="bot",
                message_type="template",
                content=f"[Template: {template_name}]",
                delivery_status="pending",
            )

    # ── Private ───────────────────────────────────────────────────────────────

    async def _get_or_404(self, automation_id: UUID) -> Automation:
        result = await self.db.execute(
            select(Automation)
            .where(
                Automation.company_id == self.company_id,
                Automation.id == automation_id,
            )
            .options(selectinload(Automation.actions))
        )
        auto = result.scalar_one_or_none()
        if not auto:
            raise NotFoundError("Automation not found")
        return auto

    def _to_response(self, auto: Automation) -> AutomationResponse:
        return AutomationResponse(
            id=auto.id,
            name=auto.name,
            description=auto.description,
            is_active=auto.is_active,
            trigger_event=auto.trigger_event,
            conditions=auto.conditions,
            actions=[
                AutomationActionResponse(
                    id=a.id,
                    action_type=a.action_type,
                    config=a.config,
                    sort_order=a.sort_order,
                )
                for a in (auto.actions or [])
            ],
            priority=auto.priority,
            execution_count=auto.execution_count,
            last_executed_at=auto.last_executed_at,
            created_at=auto.created_at,
            updated_at=auto.updated_at,
        )
