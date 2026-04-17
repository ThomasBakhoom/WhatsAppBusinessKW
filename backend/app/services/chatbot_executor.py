"""Chatbot flow execution engine - processes nodes sequentially.

Handles all node types including payment_link, check_shipping,
and standard messaging nodes.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chatbot import ChatbotFlow
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.shipping import Shipment

logger = structlog.get_logger()


class ChatbotExecutor:
    """Executes a chatbot flow's nodes for a given conversation."""

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def execute_flow(
        self,
        flow: ChatbotFlow,
        conversation_id: UUID,
        contact_id: UUID,
        inbound_message: str = "",
    ) -> list[dict[str, Any]]:
        """Execute all nodes in a flow and return outbound messages to send."""
        responses: list[dict[str, Any]] = []
        nodes = flow.nodes or []
        edges = flow.edges or []

        if not nodes:
            return responses

        # Build adjacency map
        edge_map: dict[str, list[str]] = {}
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src not in edge_map:
                edge_map[src] = []
            edge_map[src].append(tgt)

        # Start from first node
        visited: set[str] = set()
        queue = [nodes[0]["id"]]
        node_map = {n["id"]: n for n in nodes}

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)

            node = node_map.get(node_id)
            if not node:
                continue

            result = await self._execute_node(
                node, conversation_id, contact_id, inbound_message
            )
            if result:
                responses.append(result)

            # Follow edges to next node(s)
            for next_id in edge_map.get(node_id, []):
                queue.append(next_id)

        # Update execution count
        flow.execution_count = (flow.execution_count or 0) + 1
        await self.db.flush()

        return responses

    async def _execute_node(
        self,
        node: dict,
        conversation_id: UUID,
        contact_id: UUID,
        inbound_message: str,
    ) -> dict[str, Any] | None:
        """Execute a single node and return an outbound action."""
        node_type = node.get("type", "")
        data = node.get("data", {})

        if node_type == "send_message":
            return await self._node_send_message(data)

        elif node_type == "ask_question":
            return await self._node_ask_question(data)

        elif node_type == "payment_link":
            return await self._node_payment_link(data, conversation_id, contact_id)

        elif node_type == "check_shipping":
            return await self._node_check_shipping(data, contact_id)

        elif node_type == "assign_agent":
            return await self._node_assign_agent(data, conversation_id)

        elif node_type == "action":
            return await self._node_action(data, contact_id)

        elif node_type == "delay":
            # In real execution, this would pause via Celery delayed task
            seconds = int(data.get("seconds", 5))
            logger.info("chatbot_delay", seconds=seconds)
            return None

        elif node_type == "condition":
            # Condition evaluation would branch edges - simplified here
            return None

        elif node_type == "api_call":
            return await self._node_api_call(data)

        return None

    # ── Node Handlers ─────────────────────────────────────────────────

    async def _node_send_message(self, data: dict) -> dict:
        """Send a text message."""
        return {
            "action": "send_message",
            "message_type": "text",
            "content": data.get("message", ""),
        }

    async def _node_ask_question(self, data: dict) -> dict:
        """Send a question (interactive message with quick replies)."""
        question = data.get("question", "")
        options = data.get("options", [])
        return {
            "action": "send_message",
            "message_type": "interactive" if options else "text",
            "content": question,
            "metadata": {"options": options} if options else None,
        }

    async def _node_payment_link(
        self, data: dict, conversation_id: UUID, contact_id: UUID
    ) -> dict:
        """Generate a Tap Payments charge and return the payment URL.

        This is GAP 8: Payment link integration in chatbot flows.
        Config: {amount: float, currency: "KWD", description: "...", return_url: "..."}
        """
        amount = Decimal(str(data.get("amount", 0)))
        currency = data.get("currency", "KWD")
        description = data.get("description", "Payment")
        from app.config import get_settings
        domain = get_settings().app_domain.rstrip("/")
        return_url = data.get("return_url", f"{domain}/payment/success")

        # Get contact info for the charge
        contact_result = await self.db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = contact_result.scalar_one_or_none()

        # Create Tap charge
        from app.services.tap_payments import TapPaymentsService
        tap = TapPaymentsService()
        try:
            charge = await tap.create_charge(
                amount=amount,
                currency=currency,
                payment_method="knet",
                customer_email=contact.email if contact else None,
                customer_name=contact.full_name if contact else None,
                customer_phone=contact.phone if contact else None,
                description=description,
                reference_id=f"chatbot-{conversation_id}",
                return_url=return_url,
            )
            await tap.close()

            payment_url = charge.get("payment_url", "")
            charge_id = charge.get("charge_id", "")

            logger.info(
                "chatbot_payment_link_created",
                charge_id=charge_id,
                amount=float(amount),
                currency=currency,
            )

            # Send payment link message
            msg = f"Please complete your payment of {amount} {currency} for: {description}\n\nPay here: {payment_url}"

            return {
                "action": "send_message",
                "message_type": "text",
                "content": msg,
                "metadata": {
                    "payment_link": True,
                    "charge_id": charge_id,
                    "amount": float(amount),
                    "currency": currency,
                    "payment_url": payment_url,
                },
            }
        except Exception as e:
            logger.error("chatbot_payment_link_failed", error=str(e))
            await tap.close()
            return {
                "action": "send_message",
                "message_type": "text",
                "content": f"Sorry, we couldn't generate a payment link. Please contact us directly for payment.",
            }

    async def _node_check_shipping(self, data: dict, contact_id: UUID) -> dict:
        """Check shipping status for a contact's recent shipment.

        This is GAP 9: Interactive shipping chatbot query.
        Allows customers to ask "where is my order?" and get instant status.
        """
        # Find most recent shipment for this contact
        result = await self.db.execute(
            select(Shipment).where(
                Shipment.company_id == self.company_id,
                Shipment.contact_id == contact_id,
            ).order_by(Shipment.created_at.desc()).limit(1)
        )
        shipment = result.scalar_one_or_none()

        if not shipment:
            return {
                "action": "send_message",
                "message_type": "text",
                "content": "We couldn't find any recent shipments for your account. Please provide your tracking number or contact us for help.",
            }

        # Build status message
        status_messages = {
            "created": "Your order has been created and is being prepared for shipping.",
            "picked_up": "Your package has been picked up by the courier.",
            "in_transit": "Great news! Your package is on its way to you.",
            "out_for_delivery": "Your package is out for delivery today! It should arrive soon.",
            "delivered": "Your package has been delivered!",
            "failed": "Unfortunately, the delivery attempt failed. We'll try again soon.",
            "returned": "Your package is being returned. Please contact us for details.",
        }

        status_text = status_messages.get(shipment.status, f"Current status: {shipment.status}")
        tracking = shipment.tracking_number or "N/A"
        carrier = shipment.carrier or "Unknown"

        msg = (
            f"Here's your shipment status:\n\n"
            f"Tracking: {tracking}\n"
            f"Carrier: {carrier}\n"
            f"Status: {status_text}\n"
        )
        if shipment.estimated_delivery:
            msg += f"Estimated delivery: {shipment.estimated_delivery.strftime('%Y-%m-%d')}\n"

        logger.info(
            "chatbot_shipping_check",
            contact_id=str(contact_id),
            tracking=tracking,
            status=shipment.status,
        )

        return {
            "action": "send_message",
            "message_type": "text",
            "content": msg,
            "metadata": {
                "shipping_check": True,
                "tracking_number": tracking,
                "status": shipment.status,
                "carrier": carrier,
            },
        }

    async def _node_assign_agent(self, data: dict, conversation_id: UUID) -> dict:
        """Assign the conversation to a human agent."""
        from app.services.routing_engine import RoutingEngine

        conv_result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = conv_result.scalar_one_or_none()

        if conv:
            router = RoutingEngine(self.db, self.company_id)
            agent_id = await router.assign_conversation(
                conv,
                preferred_skills=data.get("skills"),
                language=data.get("language"),
            )
            if agent_id:
                conv.assigned_to_user_id = agent_id
                await self.db.flush()

        return {
            "action": "send_message",
            "message_type": "text",
            "content": data.get("message", "I'm connecting you with a team member who can help. Please hold on!"),
        }

    async def _node_action(self, data: dict, contact_id: UUID) -> dict | None:
        """Execute a CRM action (add tag, update field, etc.)."""
        action_type = data.get("action_type", "")

        if action_type == "add_tag" and data.get("tag_id"):
            from app.models.contact import ContactTag
            self.db.add(ContactTag(contact_id=contact_id, tag_id=UUID(data["tag_id"])))
            await self.db.flush()

        elif action_type == "update_lead_score" and data.get("delta"):
            from app.models.contact import Contact
            from sqlalchemy import update
            await self.db.execute(
                update(Contact).where(Contact.id == contact_id)
                .values(lead_score=Contact.lead_score + int(data["delta"]))
            )
            await self.db.flush()

        return None  # Actions don't produce outbound messages

    async def _node_api_call(self, data: dict) -> dict | None:
        """Make an external API call."""
        import httpx
        url = data.get("url", "")
        method = data.get("method", "GET").upper()
        headers = data.get("headers", {})
        body = data.get("body")

        if not url:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "POST":
                    resp = await client.post(url, json=body, headers=headers)
                else:
                    resp = await client.get(url, headers=headers)

                response_text = data.get("response_template", "API call completed.")
                return {
                    "action": "send_message",
                    "message_type": "text",
                    "content": response_text,
                    "metadata": {"api_response": resp.json() if resp.status_code == 200 else None},
                }
        except Exception as e:
            logger.error("chatbot_api_call_failed", url=url, error=str(e))
            return None
