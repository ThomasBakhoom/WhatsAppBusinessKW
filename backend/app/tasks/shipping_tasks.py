"""Celery tasks for shipping - tracking notifications via WhatsApp."""

import asyncio

import structlog
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()

STATUS_MESSAGES = {
    "created": "Your shipment has been created! Tracking: {tracking}",
    "picked_up": "Your package has been picked up by the courier. Tracking: {tracking}",
    "in_transit": "Your package is on its way! Tracking: {tracking}",
    "out_for_delivery": "Great news! Your package is out for delivery today. Tracking: {tracking}",
    "delivered": "Your package has been delivered! Thank you for your order.",
    "failed": "Delivery attempt failed. We'll try again soon. Tracking: {tracking}",
    "returned": "Your package is being returned. Please contact us for details.",
}


@celery_app.task(
    name="app.tasks.shipping.send_tracking_notification",
    bind=True,
    queue="shipping",
    max_retries=2,
)
def send_tracking_notification(
    self,
    company_id: str,
    shipment_id: str,
    contact_phone: str,
    status: str,
    tracking_number: str,
):
    """Send WhatsApp tracking notification to contact."""
    try:
        return asyncio.run(
            _async_notify(company_id, shipment_id, contact_phone, status, tracking_number)
        )
    except Exception as exc:
        logger.error("tracking_notification_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _async_notify(
    company_id: str, shipment_id: str, contact_phone: str,
    status: str, tracking_number: str,
) -> dict:
    from uuid import UUID
    from sqlalchemy import select
    from app.core.database import tenant_session
    from app.models.contact import Contact

    company_uuid = UUID(company_id)
    message = STATUS_MESSAGES.get(status, f"Shipment update: {status}").format(
        tracking=tracking_number
    )

    async with tenant_session(company_uuid) as db:
        contact_result = await db.execute(
            select(Contact).where(Contact.phone == contact_phone)
        )
        contact = contact_result.scalar_one_or_none()
        if not contact:
            return {"status": "skipped", "reason": "contact_not_found"}

        from app.services.conversation_service import ConversationService
        svc = ConversationService(db, company_uuid)
        conv = await svc.get_or_create_conversation(contact.id)
        await svc.add_message(
            conv.id,
            direction="outbound",
            sender_type="system",
            message_type="text",
            content=message,
            delivery_status="pending",
        )

    logger.info(
        "tracking_notification_sent",
        contact_phone=contact_phone,
        status=status,
        tracking=tracking_number,
    )
    return {"status": "sent", "message": message}
