"""Unit tests for contacts and tags."""

import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, suffix: str = "") -> str:
    reg = await client.post("/v1/auth/register", json={
        "email": f"contact{suffix}@test.kw", "username": f"contact{suffix}",
        "password": "TestPass123!", "company_name": f"Contact{suffix} Co",
        "first_name": "C", "last_name": "T",
    })
    return reg.json()["tokens"]["access_token"]


@pytest.mark.asyncio
class TestContacts:
    async def test_create_contact(self, client: AsyncClient):
        token = await get_auth_token(client, "c1")
        h = {"Authorization": f"Bearer {token}"}
        resp = await client.post("/v1/contacts", json={
            "phone": "+96511111111", "first_name": "Ali", "last_name": "Hassan",
        }, headers=h)
        assert resp.status_code == 201
        assert resp.json()["phone"] == "+96511111111"

    async def test_list_contacts(self, client: AsyncClient):
        token = await get_auth_token(client, "c2")
        h = {"Authorization": f"Bearer {token}"}
        await client.post("/v1/contacts", json={"phone": "+96522222222", "first_name": "A"}, headers=h)
        await client.post("/v1/contacts", json={"phone": "+96533333333", "first_name": "B"}, headers=h)
        resp = await client.get("/v1/contacts", headers=h)
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 2

    async def test_search_contacts(self, client: AsyncClient):
        token = await get_auth_token(client, "c3")
        h = {"Authorization": f"Bearer {token}"}
        await client.post("/v1/contacts", json={"phone": "+96544444444", "first_name": "Khalid"}, headers=h)
        await client.post("/v1/contacts", json={"phone": "+96555555555", "first_name": "Sara"}, headers=h)
        resp = await client.get("/v1/contacts?search=Khalid", headers=h)
        assert resp.json()["meta"]["total"] == 1

    async def test_update_contact(self, client: AsyncClient):
        token = await get_auth_token(client, "c4")
        h = {"Authorization": f"Bearer {token}"}
        created = await client.post("/v1/contacts", json={"phone": "+96566666666", "first_name": "Old"}, headers=h)
        cid = created.json()["id"]
        resp = await client.patch(f"/v1/contacts/{cid}", json={"first_name": "New"}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "New"

    async def test_delete_contact(self, client: AsyncClient):
        token = await get_auth_token(client, "c5")
        h = {"Authorization": f"Bearer {token}"}
        created = await client.post("/v1/contacts", json={"phone": "+96577777777"}, headers=h)
        cid = created.json()["id"]
        resp = await client.delete(f"/v1/contacts/{cid}", headers=h)
        assert resp.status_code == 200
        list_resp = await client.get("/v1/contacts", headers=h)
        assert list_resp.json()["meta"]["total"] == 0


@pytest.mark.asyncio
class TestTags:
    async def test_create_tag(self, client: AsyncClient):
        token = await get_auth_token(client, "t1")
        h = {"Authorization": f"Bearer {token}"}
        resp = await client.post("/v1/tags", json={"name": "VIP", "color": "#ef4444"}, headers=h)
        assert resp.status_code == 201
        assert resp.json()["name"] == "VIP"

    async def test_list_tags(self, client: AsyncClient):
        token = await get_auth_token(client, "t2")
        h = {"Authorization": f"Bearer {token}"}
        await client.post("/v1/tags", json={"name": "Tag1"}, headers=h)
        await client.post("/v1/tags", json={"name": "Tag2"}, headers=h)
        resp = await client.get("/v1/tags", headers=h)
        assert len(resp.json()) == 2

    async def test_contact_with_tags(self, client: AsyncClient):
        token = await get_auth_token(client, "t3")
        h = {"Authorization": f"Bearer {token}"}
        tag = await client.post("/v1/tags", json={"name": "Lead"}, headers=h)
        tag_id = tag.json()["id"]
        contact = await client.post("/v1/contacts", json={
            "phone": "+96588888888", "first_name": "Tagged", "tag_ids": [tag_id],
        }, headers=h)
        assert len(contact.json()["tags"]) == 1
