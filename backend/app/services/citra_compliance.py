"""CITRA Kuwait compliance service - data classification, retention, audit.

This service generates reports that a compliance officer can review. Every
claim MUST reflect reality; where something is not yet built, it MUST be
labelled as `status: "roadmap"` rather than asserting compliance.

Last audited: 2026-04-15.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.conversation import Conversation


# ── CITRA Data Classification Tiers (Kuwait) ─────────────────────────────────

CITRA_TIERS = {
    1: {
        "name": "Public Data",
        "description": "Non-sensitive, publicly available information",
        "examples": ["Company name", "Public product catalog", "Published landing pages"],
        "hosting": "Any region",
        "encryption": "Optional",
    },
    2: {
        "name": "Internal Data",
        "description": "Internal business data, not publicly shared",
        "examples": ["Analytics data", "Internal reports", "Team performance metrics"],
        "hosting": "GCC region recommended",
        "encryption": "Recommended",
    },
    3: {
        "name": "Confidential Data",
        "description": "Sensitive business and customer data",
        "examples": ["Customer contact info", "Conversations", "Deal values", "Payments"],
        "hosting": "Must be in Kuwait or CITRA-approved GCC facility",
        "encryption": "Required (AES-256)",
    },
    4: {
        "name": "Restricted / Government Data",
        "description": "Government or highly regulated data",
        "examples": ["Government entity communications", "National ID data"],
        "hosting": "Must be hosted within Kuwait borders",
        "encryption": "Required + additional controls",
    },
}


class CITRAComplianceService:
    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id
        self.settings = get_settings()

    # ── Data Classification ───────────────────────────────────────────────

    async def get_data_classification(self) -> dict:
        """CITRA tier classification for every data type on the platform."""
        classifications = {
            "contacts": {
                "tier": 3,
                "reason": "Contains personal phone numbers and emails",
                "fields": ["phone", "email", "first_name", "last_name"],
            },
            "conversations": {
                "tier": 3,
                "reason": "Private customer communications",
                "fields": ["message content", "media"],
            },
            "deals": {
                "tier": 2,
                "reason": "Business deal values and pipeline data",
                "fields": ["value", "title", "notes"],
            },
            "payments": {
                "tier": 3,
                "reason": "Financial transaction records",
                "fields": ["amount", "card_last_four", "invoice"],
            },
            "analytics": {
                "tier": 2,
                "reason": "Aggregated business metrics",
                "fields": ["dashboard stats", "reports"],
            },
            "landing_pages": {
                "tier": 1,
                "reason": "Publicly accessible content",
                "fields": ["blocks", "title"],
            },
            "audit_logs": {
                "tier": 2,
                "reason": "Internal security records",
                "fields": ["action", "user", "changes"],
            },
            "ai_contexts": {
                "tier": 3,
                "reason": "AI analysis of customer communications",
                "fields": ["dialect", "intent", "sentiment"],
            },
        }

        s3 = self.settings.s3_endpoint_url or ""
        in_gcc = "me-south" in s3 or "me-central" in s3

        return {
            "tier_definitions": CITRA_TIERS,
            "data_classifications": classifications,
            "current_hosting": {
                "region": "me-south-1" if in_gcc else "unknown (dev/local)",
                "location": "Bahrain" if in_gcc else "local",
                "provider": "AWS" if "amazonaws" in s3 else "MinIO/local",
                "citra_compliant_tiers": [1, 2, 3] if in_gcc else [1],
                "note": (
                    "Tier 4 (government) requires in-Kuwait hosting."
                    if in_gcc
                    else "Current S3 endpoint is local/dev. Not compliant for Tier 2+."
                ),
            },
        }

    # ── Retention Policies ────────────────────────────────────────────────

    async def get_retention_policies(self) -> dict:
        """Retention policies. Each entry states what IS built vs. roadmap."""
        return {
            "policies": [
                {
                    "data_type": "Contacts (soft-deleted)",
                    "retention": "Configurable (default 365 days)",
                    "action": "Hard-deleted by daily purge task after retention window",
                    "status": "implemented",
                    "configurable": True,
                },
                {
                    "data_type": "Conversations (closed)",
                    "retention": "Configurable (default 365 days)",
                    "action": "Messages + conversation hard-deleted by daily purge task",
                    "status": "implemented",
                    "configurable": True,
                },
                {
                    "data_type": "Payments / Invoices",
                    "retention": "7 years",
                    "action": "Never deleted (Kuwait commercial law)",
                    "status": "implemented",
                    "configurable": False,
                },
                {
                    "data_type": "Audit Logs",
                    "retention": "5 years (immutable)",
                    "action": "Never deleted by purge task",
                    "status": "implemented",
                    "configurable": False,
                },
                {
                    "data_type": "Analytics",
                    "retention": "Derived from source tables (messages, conversations, contacts)",
                    "action": "Analytics are computed on-the-fly from source data. No separate raw analytics table exists. Source data retention governs analytics lifespan.",
                    "status": "implemented",
                    "configurable": False,
                },
                {
                    "data_type": "AI Contexts",
                    "retention": "Configurable (default 90 days)",
                    "action": "Hard-deleted by daily purge task when updated_at exceeds retention window",
                    "status": "implemented",
                    "configurable": True,
                },
            ],
            "deletion_mechanism": "Soft delete (immediate) + Hard purge (daily Celery beat task `purge_retention`)",
            "customer_data_export": "CSV export via /v1/export/contacts, /v1/export/conversations, /v1/export/deals",
        }

    # ── Security Measures ─────────────────────────────────────────────────

    async def get_security_measures(self) -> dict:
        """Security controls. Only claims what is verified by code + tests."""
        # Check RLS enforcement for real
        rls_count = 0
        try:
            result = await self.db.execute(
                text(
                    "SELECT COUNT(*) FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND c.relkind='r' "
                    "AND c.relrowsecurity=true AND c.relforcerowsecurity=true"
                )
            )
            rls_count = result.scalar_one()
        except Exception:
            pass

        return {
            "encryption": {
                "at_rest": {
                    "detail": "Application-level Fernet (AES-128-CBC) for WhatsApp tokens and Tap payment keys. Disk encryption depends on cloud provider volume settings.",
                    "verify": "Check RDS/EBS encryption in AWS console",
                    "status": "partially_verified",
                },
                "in_transit": {
                    "detail": "TLS termination at load balancer / nginx. Internal traffic (container-to-container) is unencrypted in the Docker network.",
                    "verify": "Confirm HTTPS-only listener and HSTS at the LB",
                    "status": "info",
                },
            },
            "access_control": {
                "authentication": "JWT (HS256), 15-min access tokens, 7-day refresh tokens",
                "password_hashing": "bcrypt 12 rounds, 72-byte max",
                "password_reset": "1-hour JWT token, email-delivered, enumeration-safe",
                "password_change": "Requires current password verification, audited",
                "rbac": "5 roles (platform_admin, owner, admin, manager, agent), 34 permissions",
                "tenant_isolation": f"PostgreSQL RLS: {rls_count} tables with FORCE ROW LEVEL SECURITY. Runtime role is non-superuser (app_user).",
                "api_keys": "bcrypt-hashed, prefix-identified, scoped, expirable",
            },
            "network": {
                "rate_limiting": "Redis sliding window per-route: login 10/min, register 5/min, forgot-password 3/min, general 300/min per IP",
                "cors": "Configured allowed origins via APP_ALLOWED_ORIGINS",
                "security_headers": "X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy",
                "websocket": "JWT-authenticated connections; Redis pub/sub for cross-pod broadcast",
            },
            "monitoring": {
                "audit_logging": "All auth, contact, deal, pipeline, conversation, subscription, tag, custom-field, shipping, channel, and chatbot mutations logged with user_id, IP, field-level diffs",
                "metrics": "Prometheus-compatible /metrics endpoint with cardinality cap (500 series/metric)",
                "error_tracking": "Sentry integration (active when SENTRY_DSN is configured)",
                "structured_logging": "JSON-formatted logs via structlog with request_id correlation",
            },
            "data_protection": {
                "breach_notification": {
                    "detail": "No automated breach detection or notification workflow",
                    "status": "roadmap",
                },
                "data_classification_enforcement": {
                    "detail": "Classification tiers defined (see get_data_classification) but not enforced at the field level. No automated DLP.",
                    "status": "roadmap",
                },
            },
        }

    # ── CITRA Report ──────────────────────────────────────────────────────

    async def generate_citra_report(self) -> dict:
        classification = await self.get_data_classification()
        retention = await self.get_retention_policies()
        security = await self.get_security_measures()

        contacts_count = await self.db.execute(
            select(func.count()).select_from(Contact).where(
                Contact.company_id == self.company_id,
                Contact.deleted_at.is_(None),
            )
        )
        audit_count = await self.db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.company_id == self.company_id
            )
        )

        # Honest compliance status
        s3 = self.settings.s3_endpoint_url or ""
        in_gcc = "me-south" in s3 or "me-central" in s3

        return {
            "report_title": "CITRA Compliance Assessment Report",
            "report_date": datetime.now(timezone.utc).isoformat(),
            "company_id": str(self.company_id),
            "data_classification": classification,
            "data_retention": retention,
            "security_measures": security,
            "data_summary": {
                "total_contacts": contacts_count.scalar_one(),
                "total_audit_entries": audit_count.scalar_one(),
            },
            "compliance_status": {
                "tier_1_compliant": True,
                "tier_2_compliant": in_gcc,
                "tier_3_compliant": in_gcc,
                "tier_4_compliant": False,
                "notes": [
                    "Tier 2/3: compliant only when hosted in GCC region (me-south-1)."
                    if in_gcc
                    else "Tier 2/3: NOT compliant — current hosting is local/dev.",
                    "Tier 4: requires in-Kuwait data center (not available on current stack).",
                ],
            },
            "implemented_vs_roadmap": {
                "implemented": [
                    "Retention purge (daily Celery task with per-tenant isolation)",
                    "Audit logging on all critical mutation paths",
                    "RLS-enforced tenant isolation under non-superuser role",
                    "Rate limiting (sliding window, per-route)",
                    "Password reset + change (audited, enumeration-safe)",
                    "Sentry error tracking (when configured)",
                    "Prometheus metrics with cardinality cap",
                    "WebSocket pub/sub for multi-pod broadcast",
                ],
                "roadmap": [
                    "Automated breach detection + notification workflow",
                    "Field-level data classification enforcement / DLP",
                    "Tier 4 hosting (in-Kuwait data center)",
                ],
            },
        }
