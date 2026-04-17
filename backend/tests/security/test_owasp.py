"""OWASP Top 10 Security Tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestOWASP:
    """Security tests based on OWASP Top 10 (2021)."""

    # A01: Broken Access Control
    async def test_no_auth_returns_401(self, client: AsyncClient):
        """Endpoints must reject unauthenticated requests."""
        endpoints = [
            "/v1/contacts", "/v1/tags", "/v1/conversations",
            "/v1/automations", "/v1/pipelines", "/v1/analytics/dashboard",
            "/v1/shipping", "/v1/landing-pages",
        ]
        for ep in endpoints:
            resp = await client.get(ep)
            assert resp.status_code in (401, 403), f"{ep} should require auth"

    async def test_invalid_token_rejected(self, client: AsyncClient):
        """Forged JWT tokens must be rejected."""
        resp = await client.get("/v1/contacts", headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlIn0.fake"
        })
        assert resp.status_code in (401, 403)

    # A03: Injection
    async def test_sql_injection_in_search(self, client: AsyncClient):
        """Search parameter must not allow SQL injection."""
        reg = await client.post("/v1/auth/register", json={
            "email": "sqli@test.kw", "username": "sqli", "password": "TestPass123!",
            "company_name": "SQLi Co", "first_name": "S", "last_name": "Q",
        })
        token = reg.json()["tokens"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Attempt SQL injection via search
        resp = await client.get("/v1/contacts?search=' OR 1=1 --", headers=h)
        assert resp.status_code == 200
        # Should return 0 results, not all contacts
        assert resp.json()["meta"]["total"] == 0

    async def test_sql_injection_in_sort(self, client: AsyncClient):
        """Sort parameter must not allow SQL injection."""
        reg = await client.post("/v1/auth/register", json={
            "email": "sqli2@test.kw", "username": "sqli2", "password": "TestPass123!",
            "company_name": "SQLi2 Co", "first_name": "S", "last_name": "Q",
        })
        token = reg.json()["tokens"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/v1/contacts?sort=-created_at;DROP TABLE users", headers=h)
        # Should not crash - either 200 or 422 validation error
        assert resp.status_code in (200, 422)

    # A04: Insecure Design - IDOR
    async def test_tenant_isolation(self, client: AsyncClient):
        """User from company A must not see company B data."""
        # Company A
        reg_a = await client.post("/v1/auth/register", json={
            "email": "tenanta@test.kw", "username": "tenanta", "password": "TestPass123!",
            "company_name": "Company A", "first_name": "A", "last_name": "A",
        })
        token_a = reg_a.json()["tokens"]["access_token"]
        h_a = {"Authorization": f"Bearer {token_a}"}

        # Company B
        reg_b = await client.post("/v1/auth/register", json={
            "email": "tenantb@test.kw", "username": "tenantb", "password": "TestPass123!",
            "company_name": "Company B", "first_name": "B", "last_name": "B",
        })
        token_b = reg_b.json()["tokens"]["access_token"]
        h_b = {"Authorization": f"Bearer {token_b}"}

        # A creates contact
        contact_a = await client.post("/v1/contacts", json={
            "phone": "+96500000099", "first_name": "Secret",
        }, headers=h_a)
        cid = contact_a.json()["id"]

        # B should NOT see A's contact
        resp = await client.get(f"/v1/contacts/{cid}", headers=h_b)
        assert resp.status_code in (404, 403)

        # B should see 0 contacts
        list_b = await client.get("/v1/contacts", headers=h_b)
        assert list_b.json()["meta"]["total"] == 0

    # A07: Auth failures
    async def test_password_min_length(self, client: AsyncClient):
        """Short passwords must be rejected."""
        resp = await client.post("/v1/auth/register", json={
            "email": "short@test.kw", "username": "short", "password": "123",
            "company_name": "Short Co", "first_name": "S", "last_name": "P",
        })
        assert resp.status_code == 422

    async def test_invalid_email_format(self, client: AsyncClient):
        """Invalid emails must be rejected."""
        resp = await client.post("/v1/auth/register", json={
            "email": "not-an-email", "username": "bademail", "password": "TestPass123!",
            "company_name": "Bad Co", "first_name": "B", "last_name": "E",
        })
        assert resp.status_code == 422

    # Health endpoints (should be public)
    async def test_health_no_auth(self, client: AsyncClient):
        """Health endpoints must not require auth."""
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_metrics_accessible(self, client: AsyncClient):
        """Metrics endpoint returns data."""
        resp = await client.get("/metrics/json")
        assert resp.status_code == 200
        assert "uptime_seconds" in resp.json()

    # Webhook security
    async def test_webhook_verify_rejects_bad_token(self, client: AsyncClient):
        """Webhook verification must reject wrong token."""
        resp = await client.get(
            "/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=WRONG&hub.challenge=test"
        )
        assert resp.status_code == 403
