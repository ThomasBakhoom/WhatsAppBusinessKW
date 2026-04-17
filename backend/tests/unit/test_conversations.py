"""Unit tests for conversations and messages."""

import pytest
from httpx import AsyncClient


async def setup_user_and_contact(client: AsyncClient, suffix: str):
    reg = await client.post("/v1/auth/register", json={
        "email": f"conv{suffix}@test.kw", "username": f"conv{suffix}",
        "password": "TestPass123!", "company_name": f"Conv{suffix} Co",
        "first_name": "C", "last_name": "V",
    })
    token = reg.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    contact = await client.post("/v1/contacts", json={
        "phone": f"+9651{suffix}00000", "first_name": "Contact",
    }, headers=h)
    return token, h, contact.json()["id"]


@pytest.mark.asyncio
class TestConversations:
    async def test_start_conversation(self, client: AsyncClient):
        token, h, cid = await setup_user_and_contact(client, "cv1")
        resp = await client.post("/v1/conversations", json={
            "contact_id": cid, "message": "Hello!",
        }, headers=h)
        assert resp.status_code == 201
        assert resp.json()["status"] == "open"

    async def test_list_conversations(self, client: AsyncClient):
        token, h, cid = await setup_user_and_contact(client, "cv2")
        await client.post("/v1/conversations", json={"contact_id": cid}, headers=h)
        resp = await client.get("/v1/conversations", headers=h)
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] >= 1

    async def test_send_message(self, client: AsyncClient):
        token, h, cid = await setup_user_and_contact(client, "cv3")
        conv = await client.post("/v1/conversations", json={"contact_id": cid}, headers=h)
        conv_id = conv.json()["id"]
        msg = await client.post("/v1/conversations/messages/send", json={
            "conversation_id": conv_id, "content": "Test message",
        }, headers=h)
        assert msg.status_code == 201
        assert msg.json()["content"] == "Test message"
        assert msg.json()["direction"] == "outbound"

    async def test_get_conversation_detail(self, client: AsyncClient):
        token, h, cid = await setup_user_and_contact(client, "cv4")
        conv = await client.post("/v1/conversations", json={
            "contact_id": cid, "message": "First msg",
        }, headers=h)
        conv_id = conv.json()["id"]
        await client.post("/v1/conversations/messages/send", json={
            "conversation_id": conv_id, "content": "Second msg",
        }, headers=h)
        detail = await client.get(f"/v1/conversations/{conv_id}", headers=h)
        assert detail.status_code == 200
        assert len(detail.json()["messages"]) >= 2

    async def test_update_conversation_status(self, client: AsyncClient):
        token, h, cid = await setup_user_and_contact(client, "cv5")
        conv = await client.post("/v1/conversations", json={"contact_id": cid}, headers=h)
        conv_id = conv.json()["id"]
        resp = await client.patch(f"/v1/conversations/{conv_id}", json={"status": "closed"}, headers=h)
        assert resp.json()["status"] == "closed"
