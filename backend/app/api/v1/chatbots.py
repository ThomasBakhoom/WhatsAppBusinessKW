"""Chatbot flow builder API."""

from uuid import UUID
from fastapi import APIRouter, Request
from app.dependencies import AuthUser, TenantDbSession
from app.schemas.chatbots import ChatbotFlowCreate, ChatbotFlowResponse, ChatbotFlowUpdate
from app.schemas.common import SuccessResponse
from app.services.actor import actor_from_request
from app.services.chatbot_service import ChatbotService

router = APIRouter()


@router.get("", response_model=list[ChatbotFlowResponse])
async def list_flows(db: TenantDbSession, user: AuthUser):
    return await ChatbotService(db, user.company_id).list_flows()


@router.post("", response_model=ChatbotFlowResponse, status_code=201)
async def create_flow(data: ChatbotFlowCreate, db: TenantDbSession, user: AuthUser, request: Request):
    f = await ChatbotService(db, user.company_id, actor=actor_from_request(user, request)).create_flow(data)
    await db.commit()
    return f


@router.get("/{flow_id}", response_model=ChatbotFlowResponse)
async def get_flow(flow_id: UUID, db: TenantDbSession, user: AuthUser):
    return await ChatbotService(db, user.company_id).get_flow(flow_id)


@router.patch("/{flow_id}", response_model=ChatbotFlowResponse)
async def update_flow(flow_id: UUID, data: ChatbotFlowUpdate, db: TenantDbSession, user: AuthUser, request: Request):
    f = await ChatbotService(db, user.company_id, actor=actor_from_request(user, request)).update_flow(flow_id, data)
    await db.commit()
    return f


@router.delete("/{flow_id}", response_model=SuccessResponse)
async def delete_flow(flow_id: UUID, db: TenantDbSession, user: AuthUser, request: Request):
    await ChatbotService(db, user.company_id, actor=actor_from_request(user, request)).delete_flow(flow_id)
    await db.commit()
    return SuccessResponse(message="Flow deleted")


@router.post("/{flow_id}/toggle", response_model=ChatbotFlowResponse)
async def toggle_flow(flow_id: UUID, db: TenantDbSession, user: AuthUser, request: Request):
    f = await ChatbotService(db, user.company_id, actor=actor_from_request(user, request)).toggle_flow(flow_id)
    await db.commit()
    return f
