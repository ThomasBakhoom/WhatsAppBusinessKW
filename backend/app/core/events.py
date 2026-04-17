"""Internal event bus for domain event publishing and subscribing."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import UUID

import structlog

logger = structlog.get_logger()

EventHandler = Callable[..., Coroutine[Any, Any, None]]


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_type: str
    company_id: UUID
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))


class EventBus:
    """In-process event bus for publishing and subscribing to domain events."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)
        logger.info("event_handler_registered", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        self._handlers[event_type].remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribed handlers."""
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return

        logger.info(
            "event_published",
            event_type=event.event_type,
            event_id=event.event_id,
            handler_count=len(handlers),
        )

        # Fire handlers concurrently but don't fail the main operation
        tasks = []
        for handler in handlers:
            tasks.append(self._safe_handle(handler, event))
        await asyncio.gather(*tasks)

    async def _safe_handle(self, handler: EventHandler, event: DomainEvent) -> None:
        """Execute handler with error isolation."""
        try:
            await handler(event)
        except Exception:
            logger.exception(
                "event_handler_failed",
                event_type=event.event_type,
                handler=handler.__name__,
            )


# Singleton event bus
event_bus = EventBus()


# Event type constants
class Events:
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    MESSAGE_STATUS_CHANGED = "message.status_changed"
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_ASSIGNED = "conversation.assigned"
    DEAL_CREATED = "deal.created"
    DEAL_STAGE_CHANGED = "deal.stage_changed"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    SHIPMENT_STATUS_CHANGED = "shipment.status_changed"
    AUTOMATION_TRIGGERED = "automation.triggered"
