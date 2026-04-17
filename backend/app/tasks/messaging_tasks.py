"""Celery tasks for sending WhatsApp messages."""

import asyncio

import structlog
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.messaging.send_whatsapp",
    bind=True,
    queue="messaging",
    max_retries=3,
    default_retry_delay=30,
)
def send_whatsapp_message(
    self,
    message_id: str,
    company_id: str,
    to: str,
    message_type: str,
    content: str | None = None,
    media_url: str | None = None,
    template_name: str | None = None,
    template_language: str | None = None,
    template_params: list[str] | None = None,
):
    """Send a WhatsApp message via Cloud API and update delivery status."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _async_send(
                message_id=message_id,
                company_id=company_id,
                to=to,
                message_type=message_type,
                content=content,
                media_url=media_url,
                template_name=template_name,
                template_language=template_language,
                template_params=template_params,
            )
        )
        loop.close()
        return result
    except Exception as exc:
        logger.error("whatsapp_send_failed", message_id=message_id, error=str(exc))
        raise self.retry(exc=exc)


async def _async_send(
    *,
    message_id: str,
    company_id: str,
    to: str,
    message_type: str,
    content: str | None,
    media_url: str | None,
    template_name: str | None,
    template_language: str | None,
    template_params: list[str] | None,
) -> dict:
    """Execute the send within an async context.

    Runs under the company's tenant context so RLS-protected reads/writes of
    `messages` succeed under the non-superuser runtime role. `companies` is
    not RLS-protected, but reading it inside the tenant_session is safe.
    """
    from uuid import UUID
    from sqlalchemy import select
    from app.core.database import tenant_session
    from app.models.company import Company
    from app.models.message import Message
    from app.services.whatsapp.cloud_api import CloudAPIProvider
    from app.services.whatsapp.base import OutboundMessage, MessageType

    company_uuid = UUID(company_id)
    msg_uuid = UUID(message_id)

    async with tenant_session(company_uuid) as db:
        # Get company's WhatsApp config (companies has no RLS)
        result = await db.execute(
            select(Company).where(Company.id == company_uuid)
        )
        company = result.scalar_one_or_none()
        if not company or not company.whatsapp_phone_number_id:
            msg_result = await db.execute(
                select(Message).where(Message.id == msg_uuid)
            )
            msg = msg_result.scalar_one_or_none()
            if msg:
                msg.delivery_status = "failed"
                msg.delivery_error = "WhatsApp not configured"
            return {"status": "failed", "error": "WhatsApp not configured"}

        provider = CloudAPIProvider(
            access_token=company.whatsapp_token or "",
            phone_number_id=company.whatsapp_phone_number_id,
            verify_token="",
        )

        # Build outbound message
        if message_type == "text":
            msg_content = {"body": content or ""}
        elif message_type == "template" and template_name:
            msg_content = {
                "name": template_name,
                "language": {"code": template_language or "en"},
            }
            if template_params:
                msg_content["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in template_params],
                }]
        elif media_url:
            msg_content = {"link": media_url}
        else:
            msg_content = {"body": content or ""}

        outbound = OutboundMessage(
            to=to,
            message_type=MessageType(message_type) if message_type in [e.value for e in MessageType] else MessageType.TEXT,
            content=msg_content,
        )

    # Send outside the DB transaction. If we kept the DB tx open across the
    # network round-trip we'd hold a connection (and the SET LOCAL GUC) for
    # the full WhatsApp call.
    send_error: Exception | None = None
    external_id: str | None = None
    try:
        external_id = await provider.send_message(outbound)
    except Exception as e:
        send_error = e
    finally:
        await provider.close()

    # Persist the result in a fresh tenant session so failure-status writes
    # aren't rolled back if we re-raise below.
    async with tenant_session(company_uuid) as db:
        msg_result = await db.execute(
            select(Message).where(Message.id == msg_uuid)
        )
        msg = msg_result.scalar_one_or_none()
        if msg:
            if send_error is None:
                msg.external_id = external_id
                msg.delivery_status = "sent"
            else:
                msg.delivery_status = "failed"
                msg.delivery_error = str(send_error)

    if send_error is not None:
        raise send_error
    return {"status": "sent", "external_id": external_id}
