"""Unit tests for automations."""

import pytest
from httpx import AsyncClient


async def get_token(client: AsyncClient, suffix: str) -> tuple[str, dict]:
    reg = await client.post("/v1/auth/register", json={
        "email": f"auto{suffix}@test.kw", "username": f"auto{suffix}",
        "password": "TestPass123!", "company_name": f"Auto{suffix} Co",
        "first_name": "A", "last_name": "U",
    })
    token = reg.json()["tokens"]["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestAutomations:
    async def test_create_automation(self, client: AsyncClient):
        _, h = await get_token(client, "a1")
        resp = await client.post("/v1/automations", json={
            "name": "Test Auto",
            "trigger_event": "message.received",
            "actions": [{"action_type": "auto_reply", "config": {"message": "Hi!"}, "sort_order": 0}],
        }, headers=h)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test Auto"
        assert len(resp.json()["actions"]) == 1

    async def test_list_automations(self, client: AsyncClient):
        _, h = await get_token(client, "a2")
        await client.post("/v1/automations", json={
            "name": "Auto 1", "trigger_event": "message.received",
            "actions": [{"action_type": "auto_reply", "config": {}, "sort_order": 0}],
        }, headers=h)
        resp = await client.get("/v1/automations", headers=h)
        assert len(resp.json()) >= 1

    async def test_toggle_automation(self, client: AsyncClient):
        _, h = await get_token(client, "a3")
        created = await client.post("/v1/automations", json={
            "name": "Toggle Me", "trigger_event": "contact.created",
            "actions": [{"action_type": "add_tag", "config": {}, "sort_order": 0}],
        }, headers=h)
        aid = created.json()["id"]
        assert created.json()["is_active"] is True
        toggled = await client.post(f"/v1/automations/{aid}/toggle", headers=h)
        assert toggled.json()["is_active"] is False

    async def test_automation_with_conditions(self, client: AsyncClient):
        _, h = await get_token(client, "a4")
        resp = await client.post("/v1/automations", json={
            "name": "Conditional",
            "trigger_event": "message.received",
            "conditions": [{"field": "message.content", "operator": "contains", "value": "price"}],
            "actions": [{"action_type": "update_lead_score", "config": {"delta": 5}, "sort_order": 0}],
        }, headers=h)
        assert resp.status_code == 201
        assert len(resp.json()["conditions"]) == 1

    async def test_delete_automation(self, client: AsyncClient):
        _, h = await get_token(client, "a5")
        created = await client.post("/v1/automations", json={
            "name": "Delete Me", "trigger_event": "message.received",
            "actions": [{"action_type": "auto_reply", "config": {}, "sort_order": 0}],
        }, headers=h)
        aid = created.json()["id"]
        resp = await client.delete(f"/v1/automations/{aid}", headers=h)
        assert resp.status_code == 200
