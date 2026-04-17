"""Integration tests - end-to-end flows across multiple services."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthToContactFlow:
    """Register -> Login -> Create Contact -> Tag -> Search -> Delete."""

    async def test_full_crm_flow(self, client: AsyncClient):
        # Register
        reg = await client.post("/v1/auth/register", json={
            "email": "flow1@test.kw", "username": "flow1", "password": "TestPass123!",
            "company_name": "Flow1 Co", "first_name": "Flow", "last_name": "One",
        })
        assert reg.status_code == 201
        token = reg.json()["tokens"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Verify profile
        me = await client.get("/v1/auth/me", headers=h)
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "flow1@test.kw"

        # Create tag
        tag = await client.post("/v1/tags", json={"name": "VIP", "color": "#ef4444"}, headers=h)
        assert tag.status_code == 201
        tag_id = tag.json()["id"]

        # Create contact with tag
        contact = await client.post("/v1/contacts", json={
            "phone": "+96500000001", "first_name": "Ahmed", "last_name": "Al-Sabah",
            "email": "ahmed@test.kw", "tag_ids": [tag_id],
        }, headers=h)
        assert contact.status_code == 201
        assert len(contact.json()["tags"]) == 1
        cid = contact.json()["id"]

        # Search
        search = await client.get("/v1/contacts?search=Ahmed", headers=h)
        assert search.json()["meta"]["total"] == 1

        # Filter by tag
        tagged = await client.get(f"/v1/contacts?tag_id={tag_id}", headers=h)
        assert tagged.json()["meta"]["total"] == 1

        # Update contact
        updated = await client.patch(f"/v1/contacts/{cid}", json={
            "notes": "Key customer", "status": "active",
        }, headers=h)
        assert updated.json()["notes"] == "Key customer"

        # Delete
        deleted = await client.delete(f"/v1/contacts/{cid}", headers=h)
        assert deleted.status_code == 200

        # Verify deleted (soft)
        listed = await client.get("/v1/contacts", headers=h)
        assert listed.json()["meta"]["total"] == 0


@pytest.mark.asyncio
class TestConversationMessageFlow:
    """Create Contact -> Start Conversation -> Send Messages -> Close."""

    async def test_full_messaging_flow(self, client: AsyncClient):
        reg = await client.post("/v1/auth/register", json={
            "email": "flow2@test.kw", "username": "flow2", "password": "TestPass123!",
            "company_name": "Flow2 Co", "first_name": "F", "last_name": "T",
        })
        token = reg.json()["tokens"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Create contact
        contact = await client.post("/v1/contacts", json={
            "phone": "+96500000002", "first_name": "Khalid",
        }, headers=h)
        cid = contact.json()["id"]

        # Start conversation with initial message
        conv = await client.post("/v1/conversations", json={
            "contact_id": cid, "message": "Hello Khalid!",
        }, headers=h)
        assert conv.status_code == 201
        conv_id = conv.json()["id"]

        # Send more messages
        msg1 = await client.post("/v1/conversations/messages/send", json={
            "conversation_id": conv_id, "content": "How can I help?",
        }, headers=h)
        assert msg1.status_code == 201

        msg2 = await client.post("/v1/conversations/messages/send", json={
            "conversation_id": conv_id, "content": "We have a special offer!",
        }, headers=h)
        assert msg2.status_code == 201

        # Get conversation detail
        detail = await client.get(f"/v1/conversations/{conv_id}", headers=h)
        assert len(detail.json()["messages"]) >= 3

        # Close conversation
        closed = await client.patch(f"/v1/conversations/{conv_id}", json={"status": "closed"}, headers=h)
        assert closed.json()["status"] == "closed"

        # Verify in list
        convs = await client.get("/v1/conversations?status=closed", headers=h)
        assert convs.json()["meta"]["total"] >= 1


@pytest.mark.asyncio
class TestPipelineDealFlow:
    """Create Pipeline -> Add Deals -> Move -> Win -> Analytics."""

    async def test_full_pipeline_flow(self, client: AsyncClient):
        reg = await client.post("/v1/auth/register", json={
            "email": "flow3@test.kw", "username": "flow3", "password": "TestPass123!",
            "company_name": "Flow3 Co", "first_name": "F", "last_name": "T",
        })
        token = reg.json()["tokens"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Create pipeline
        pipeline = await client.post("/v1/pipelines", json={
            "name": "Test Pipeline",
            "stages": [
                {"name": "New", "color": "#6366f1", "sort_order": 0},
                {"name": "Proposal", "color": "#f97316", "sort_order": 1},
                {"name": "Won", "color": "#22c55e", "sort_order": 2, "is_won": True},
            ],
        }, headers=h)
        pid = pipeline.json()["id"]
        stages = pipeline.json()["stages"]

        # Create deals
        deal1 = await client.post("/v1/pipelines/deals", json={
            "pipeline_id": pid, "stage_id": stages[0]["id"],
            "title": "Deal Alpha", "value": 5000,
        }, headers=h)
        d1_id = deal1.json()["id"]

        deal2 = await client.post("/v1/pipelines/deals", json={
            "pipeline_id": pid, "stage_id": stages[0]["id"],
            "title": "Deal Beta", "value": 3000,
        }, headers=h)

        # Kanban board
        board = await client.get(f"/v1/pipelines/{pid}/board", headers=h)
        assert board.json()["columns"][0]["deal_count"] == 2

        # Move deal to Proposal
        await client.post(f"/v1/pipelines/deals/{d1_id}/move", json={
            "stage_id": stages[1]["id"], "position": 0,
        }, headers=h)

        # Win deal
        won = await client.patch(f"/v1/pipelines/deals/{d1_id}", json={
            "status": "won", "stage_id": stages[2]["id"],
        }, headers=h)
        assert won.json()["status"] == "won"

        # Check activities
        activities = await client.get(f"/v1/pipelines/deals/{d1_id}/activities", headers=h)
        types = [a["activity_type"] for a in activities.json()]
        assert "created" in types
        assert "stage_changed" in types

        # Analytics
        analytics = await client.get("/v1/analytics/dashboard?days=30", headers=h)
        assert analytics.status_code == 200
