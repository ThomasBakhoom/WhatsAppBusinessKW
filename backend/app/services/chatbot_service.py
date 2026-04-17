"""Chatbot flow service - CRUD + execution engine."""

from uuid import UUID
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundError
from app.models.chatbot import ChatbotFlow
from app.schemas.chatbots import ChatbotFlowCreate, ChatbotFlowResponse, ChatbotFlowUpdate
from app.services.actor import Actor
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class ChatbotService:
    def __init__(self, db: AsyncSession, company_id: UUID, actor: Actor | None = None):
        self.db = db
        self.company_id = company_id
        self._audit = AuditService(db, company_id, actor=actor)

    async def list_flows(self) -> list[ChatbotFlowResponse]:
        result = await self.db.execute(
            select(ChatbotFlow).where(ChatbotFlow.company_id == self.company_id)
            .order_by(ChatbotFlow.name)
        )
        return [self._to_response(f) for f in result.scalars().all()]

    async def get_flow(self, flow_id: UUID) -> ChatbotFlowResponse:
        return self._to_response(await self._get_or_404(flow_id))

    async def create_flow(self, data: ChatbotFlowCreate) -> ChatbotFlowResponse:
        flow = ChatbotFlow(
            company_id=self.company_id, name=data.name, description=data.description,
            trigger_type=data.trigger_type, trigger_config=data.trigger_config,
            nodes=[n.model_dump() for n in data.nodes],
            edges=[e.model_dump() for e in data.edges],
        )
        self.db.add(flow)
        await self.db.flush()

        await self._audit.log(
            action="chatbot.created",
            description=f"Chatbot '{flow.name}' created",
            resource_type="chatbot",
            resource_id=str(flow.id),
            changes={
                "name": flow.name, "trigger_type": flow.trigger_type,
                "description": flow.description,
            },
        )

        return self._to_response(flow)

    async def update_flow(self, flow_id: UUID, data: ChatbotFlowUpdate) -> ChatbotFlowResponse:
        flow = await self._get_or_404(flow_id)
        update = data.model_dump(exclude_unset=True, exclude={"nodes", "edges"})
        diff: dict = {}
        for k, v in update.items():
            old_value = getattr(flow, k, None)
            if old_value != v:
                diff[k] = {"old": old_value, "new": v}
            setattr(flow, k, v)
        if data.nodes is not None:
            diff["nodes"] = {"changed": True}
            flow.nodes = [n.model_dump() for n in data.nodes]
        if data.edges is not None:
            diff["edges"] = {"changed": True}
            flow.edges = [e.model_dump() for e in data.edges]
        await self.db.flush()

        if diff:
            await self._audit.log(
                action="chatbot.updated",
                description=f"Chatbot '{flow.name}' updated",
                resource_type="chatbot",
                resource_id=str(flow.id),
                changes=diff,
            )

        return self._to_response(flow)

    async def delete_flow(self, flow_id: UUID) -> None:
        flow = await self._get_or_404(flow_id)
        flow_name = flow.name
        flow_id_str = str(flow.id)
        await self.db.delete(flow)
        await self.db.flush()

        await self._audit.log(
            action="chatbot.deleted",
            description=f"Chatbot '{flow_name}' deleted",
            resource_type="chatbot",
            resource_id=flow_id_str,
            changes={"name": flow_name},
        )

    async def toggle_flow(self, flow_id: UUID) -> ChatbotFlowResponse:
        flow = await self._get_or_404(flow_id)
        old_active = flow.is_active
        flow.is_active = not flow.is_active
        await self.db.flush()

        action = "chatbot.activated" if flow.is_active else "chatbot.deactivated"
        await self._audit.log(
            action=action,
            description=f"Chatbot '{flow.name}' {'activated' if flow.is_active else 'deactivated'}",
            resource_type="chatbot",
            resource_id=str(flow.id),
            changes={"is_active": {"old": old_active, "new": flow.is_active}},
        )

        return self._to_response(flow)

    async def match_inbound(self, message_content: str) -> ChatbotFlow | None:
        """Find a matching active flow for an inbound message."""
        result = await self.db.execute(
            select(ChatbotFlow).where(
                ChatbotFlow.company_id == self.company_id,
                ChatbotFlow.is_active == True,
            )
        )
        for flow in result.scalars().all():
            if flow.trigger_type == "keyword":
                keywords = flow.trigger_config.get("keywords", [])
                match_type = flow.trigger_config.get("match_type", "contains")
                lower = message_content.lower()
                for kw in keywords:
                    if match_type == "exact" and lower == kw.lower():
                        return flow
                    elif match_type == "contains" and kw.lower() in lower:
                        return flow
            elif flow.trigger_type == "message_received":
                return flow
        return None

    async def _get_or_404(self, flow_id: UUID) -> ChatbotFlow:
        result = await self.db.execute(
            select(ChatbotFlow).where(
                ChatbotFlow.company_id == self.company_id, ChatbotFlow.id == flow_id
            )
        )
        f = result.scalar_one_or_none()
        if not f:
            raise NotFoundError("Chatbot flow not found")
        return f

    def _to_response(self, f: ChatbotFlow) -> ChatbotFlowResponse:
        return ChatbotFlowResponse(
            id=f.id, name=f.name, description=f.description, is_active=f.is_active,
            trigger_type=f.trigger_type, trigger_config=f.trigger_config,
            nodes=f.nodes, edges=f.edges, execution_count=f.execution_count,
            created_at=f.created_at, updated_at=f.updated_at,
        )
