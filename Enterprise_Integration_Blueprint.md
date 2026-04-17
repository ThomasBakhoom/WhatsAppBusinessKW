# Enterprise Integration Blueprint: Kuwait WhatsApp Growth Engine (v0.1.0)

*Prepared for: Third-party integration partner architects*
*Audit date: 13 April 2026*
*Source of record: `D:\Work\Kuwait WhatsApp Growth Engine\App` (commit state at audit time)*

---

## 1. Executive Strategic Summary

The Kuwait WhatsApp Growth Engine ("KWGE") is a multi-tenant, WhatsApp-first commercial engagement platform purpose-built for the Kuwaiti and broader GCC market. It pairs a FastAPI/Python 3.11 service-oriented backend with a Next.js 15 / React 19 operator console and is deployed to AWS `me-south-1` (Bahrain) for in-region data residency. The system reaches a credible 78% feature-completeness against its own product specification (per `GAP_ANALYSIS.md:53`) and a self-assessed enterprise readiness of 7.6/10, anchored by genuine differentiators — Cloud-API-native WhatsApp messaging, K-Net/Tap Payments, Aramex shipping, Kuwaiti-dialect NLP, and CITRA-aligned compliance instrumentation. For an integration partner, the platform's principal strengths are a clean async REST surface, idempotent webhook contracts, and a strict tenant-scoped data model. Its principal risks are an in-memory WebSocket fanout that will not survive horizontal scaling, an Alembic baseline that does not reflect the live ORM schema, an HS256-signed JWT scheme, and four critical product surfaces (campaign broadcast, omnichannel, chatbot executor, Twilio fallback) that exist in the data model but are not production-functional. Integration is feasible on a 2–4 week deployment horizon, with a recommended 8-week hardening path before binding to external SLAs.

---

## 2. Architectural Topography & Design Evaluation

### 2.1 Paradigm & Patterns

KWGE is a **modular monolith with asynchronous task offload**, not a true microservice topology. A single FastAPI process exposes 31 versioned API modules under `/v1/*` (`backend/app/api/router.py`), and a Celery worker fleet (eight named queues — `default,messaging,automations,webhooks,analytics,imports,shipping,ai`, per `docker/docker-compose.yml:145`) shares the same code image and database. Cross-cutting concerns are implemented as ordered ASGI middleware (`backend/app/main.py:64-74`): `SecurityHeadersMiddleware → TenantMiddleware → TimingMiddleware → RequestIDMiddleware → CORSMiddleware`. The pattern fidelity is high for a monolith — domain logic is segregated into `services/`, persistence into `models/`, and transport into `api/v1/` — but the absence of bounded-context boundaries between, e.g., `payments`, `shipping`, and `messaging` means all domains share a single connection pool, a single deploy artefact, and a single failure domain.

### 2.2 Component Decomposition

| Logical component | Code location | Bounded responsibility | Communication mode |
|---|---|---|---|
| API gateway (FastAPI) | `backend/app/main.py` | HTTP/WebSocket ingress, auth, tenancy, metrics | Synchronous REST + WS |
| Conversation service | `backend/app/services/*_service.py` | Contacts, conversations, messages, routing | In-process calls |
| WhatsApp provider abstraction | `backend/app/services/whatsapp/` | Cloud API (prod), Twilio (stub) | Outbound HTTPS, inbound webhook |
| AI/NLP engine | `backend/app/services/ai/` | Kuwaiti dialect, intent, sentiment | Anthropic Claude API + rule fallback |
| Payments | `backend/app/services/tap_payments.py` | Tap charges, K-Net, Apple Pay, refunds | Outbound HTTPS + webhook |
| Shipping | `backend/app/services/shipping/aramex.py` | Aramex create/track/cancel + COD | Outbound HTTPS |
| Worker fleet | `backend/app/tasks/` | Async send, imports, analytics, AI batch | Celery over Redis |
| Realtime fanout | `backend/app/websocket/` | Per-company / per-user broadcast | In-memory `ConnectionManager` (see §7) |
| Operator console | `frontend/src/app/` | Inbox, CRM, pipeline, campaigns, settings | REST + WS to API |

### 2.3 Data Flow & State Management

The dominant write path is asynchronous: an inbound WhatsApp event arrives at `POST /webhooks/whatsapp` (`backend/app/api/v1/webhooks.py:40-60`), is parsed by `CloudAPIProvider.parse_webhook()`, persisted as a `Message` row, and broadcast via WebSocket to the assigned agent. Outbound messages are stored as `pending`, dispatched by the `messaging` Celery queue, and reconciled to `delivered/read/failed` when Meta posts a status update — a textbook eventually-consistent pattern with the WhatsApp `message.id` as the idempotency key. Synchronous request/response is reserved for CRUD and analytics queries. Strong consistency is enforced inside a single tenant via PostgreSQL transactions; cross-tenant isolation is enforced at the application layer plus a session-scoped `SET LOCAL app.current_tenant` GUC (`backend/app/core/database.py:60`), but **no PostgreSQL row-level security policies are defined** — isolation is therefore only as strong as the ORM filter discipline.

---

## 3. The Integration Surface Area (API & Contract Analysis)

This section is the operational contract a partner will bind to. All paths are prefixed by the public base URL plus `/v1` (e.g., `https://api.kwgrowth.example/v1/...`); WebSocket is served at `/ws`.

### 3.1 Exposed Interfaces — REST Catalogue

The following table lists every router registered in `backend/app/api/router.py`. Auth column: ✓ = JWT bearer required; ⊘ = unauthenticated (webhook or health).

| Module | Prefix | Representative methods | Auth | Notes |
|---|---|---|---|---|
| auth | `/auth` | `POST /register`, `/login`, `/refresh` | ⊘ → JWT | Access token 15 min, refresh 7 d (`backend/app/config.py:40-41`) |
| contacts | `/contacts` | `GET`, `POST`, `PATCH`, `DELETE` (soft) | ✓ | `ilike` search; filters: status, source, tag, agent |
| conversations | `/conversations` | list/create/detail/PATCH status & assignment; `POST /{id}/messages` | ✓ | Triggers `send_whatsapp_message` Celery task |
| webhooks | `/webhooks/whatsapp` | `GET` verify, `POST` events | ⊘ | `hub.verify_token` handshake; raw Meta payload |
| instagram_webhooks | `/webhooks/instagram` | `POST` | ⊘ | **Partial** — model present, parser stubbed |
| tags | `/tags` | full CRUD | ✓ | Unique per company |
| custom_fields | `/custom-fields` | list, create | ✓ | 5 field types |
| automations | `/automations` | full CRUD | ✓ | 7 operators × 8 actions, rule engine |
| ai | `/ai` | `POST /analyze` | ✓ | Dialect, intent, sentiment; Claude fallback to rules |
| chatbots | `/chatbots` | CRUD over flow graph (nodes/edges JSON) | ✓ | Executor **partial** (see §7) |
| pipelines | `/pipelines` | stages, deals, activities | ✓ | Kanban model |
| payments | `/payments` | `GET /plans`, `POST /create-charge`, `GET /charge/{id}`, `POST /webhook` | ✓ (webhook ⊘) | Tap (K-Net, Visa, MC, Apple Pay) |
| shipping | `/shipping` | `POST /create-shipment`, `GET /track`, `POST /cancel` | ✓ | Aramex; mock when key empty |
| landing_pages | `/landing-pages` | CRUD | ✓ | 8 block types; public render |
| campaigns | `/campaigns` | CRUD | ✓ | **Send pipeline not implemented** |
| analytics | `/analytics` | `/dashboard`, `/messages`, `/pipeline`, `/team`, `/lp`, `/automations` | ✓ | Six categories |
| compliance | `/compliance` | `/status`, `/report`, `/audit-log` | ✓ | 8 CITRA checks |
| users | `/users` | invite, role, deactivate | ✓ | API present, no UI (gap #4) |
| export | `/export` | `POST /contacts`, `/conversations` | ✓ | CSV; async via Celery |
| templates | `/templates` | list, `PATCH /sync-whatsapp` | ✓ | **Meta auto-sync stub** (gap #10) |
| catalog | `/catalog` | products CRUD, `POST /sync-whatsapp` | ✓ | WhatsApp Catalog abstraction |
| surveys | `/surveys` | CSAT lifecycle | ✓ | UI partial |
| media | `/media` | `POST /upload`, `GET /{id}/download` | ✓ | S3/MinIO backed |
| qrcode | `/qr` | `POST /generate` | ✓ | WhatsApp lead-capture |
| glossary | `/glossary` | term CRUD | ✓ | Tenant business terms |
| timeline | `/timeline/{contact_id}` | `GET` | ✓ | Unified contact event stream |
| channels | `/channels` | list, `PATCH config` | ✓ | WhatsApp live; IG/FB/Snap stubs |

**Operational endpoints** (`backend/app/main.py:141-173`): `GET /health`, `GET /health/ready` (DB + Redis probes, returns 503 on failure), `GET /metrics` (Prometheus text), `GET /metrics/json`.

**WebSocket** (`backend/app/main.py:113-138`): `WS /ws?token={jwt}`. Access-type tokens only; non-access tokens are rejected with close code `4001`. Application-level keepalive: client sends `"ping"`, server replies `"pong"`. Broadcasts are scoped per-company or per-user.

### 3.2 Authentication & Authorization

- **Scheme.** OAuth-style password grant returning a JWT pair. Algorithm is **HS256 with a shared secret** (`backend/app/core/security.py:28-65`, `backend/app/config.py:39`). For a partner integrating server-to-server, this is functional but suboptimal: secret leakage allows token forgery, and HS256 prevents the partner from independently verifying tokens against a public key.
- **Token claims.** `sub` (user UUID), `company_id`, `roles[]`, `iat`, `exp`, `type` ∈ {`access`, `refresh`}.
- **Lifetimes.** 15 min access / 7 d refresh — both configurable.
- **Tenant scope.** Every authenticated dependency injects `company_id` from the JWT and applies it both via ORM `WHERE` clauses and via `SET LOCAL app.current_tenant`.
- **RBAC.** Five roles (`platform_admin`, `owner`, `admin`, `manager`, `agent`) with ≈30 permissions stored as a JSONB array on `users`. Enforcement is **manual per endpoint** — there is no `@require_permission` decorator, which creates audit risk on new endpoints added by the partner.
- **Webhook auth.** WhatsApp uses Meta's `hub.verify_token` handshake against `WHATSAPP_VERIFY_TOKEN`. Tap and Aramex webhooks rely on bearer secret in headers; **payload signature verification is not present in the reviewed code** for either. Partners introducing new webhook producers must add HMAC validation.
- **Password storage.** bcrypt, 12 rounds, truncated to 72 bytes per spec (`backend/app/core/security.py:18-20`).

### 3.3 Data Contracts & Schemas

All request/response bodies are validated by Pydantic; UUIDs, ISO-8601 timestamps, regex-constrained enums (e.g., conversation status `^(open|closed|pending|snoozed)$`, `backend/app/api/v1/conversations.py:33`) and email-validator-backed addresses are enforced at the edge. Currency is always **KWD with 3 decimal places** in payments and deals — partners must not assume 2-dp ISO 4217. Phone numbers are normalised to E.164 in `phone_utils`.

Notable JSONB-backed contracts that a partner will inevitably touch:

- `Automation.conditions` — array of `{field, op ∈ [eq, neq, gt, gte, lt, lte, contains], value}`; AND-evaluated.
- `Automation.actions` — sequential action list across 8 types, including `webhook` (forwards to a partner URL via the `webhooks` Celery queue).
- `Chatbot.nodes` / `Chatbot.edges` — graph form with node `type` ∈ {message, condition, payment_link, check_shipping, …}. The node schema is canonical for any flow-builder partners may build.
- `AuditLog.changes` — immutable JSONB diff per entity mutation, indexed by `(entity_type, entity_id)`.

**Versioning.** All routes are pinned under `/v1`. There is no API deprecation header convention; partners should expect breaking changes to be communicated out-of-band.

### 3.4 External Dependencies (the platform's upstream cone)

These are the systems the platform itself depends upon and whose availability bounds the partner's effective SLA:

| Upstream | Endpoint | Auth | Failure mode encoded |
|---|---|---|---|
| Meta WhatsApp Cloud API | `https://graph.facebook.com/v19.0` | Bearer | Celery retry; status reconciled via webhook |
| Tap Payments | `https://api.tap.company/v2` | Bearer (secret key) | Mock fallback when key empty (dev) |
| Aramex Shipping | `https://ws.aramex.net/.../Service_1_0.svc/json` | Bearer | Mock fallback; cancel is a stub returning `True` |
| Anthropic Claude | (default Claude endpoint) | Bearer (`ANTHROPIC_API_KEY`) | Rule-based `kuwaiti_nlp.py` fallback |
| AWS S3 / MinIO | Region endpoint | SigV4 / static creds | None — failures propagate |
| AWS RDS / ElastiCache | VPC-internal | IAM / password | Health probe surfaces via `/health/ready` |

The absence of an explicit circuit breaker (see §6) means a sustained outage at Meta or Tap will manifest as queue back-pressure rather than fast failure — partners depending on KWGE's outbound calls should plan for that latency profile.

---

## 4. Technology Stack & Infrastructure Landscape

**Core stack.** Python 3.11 (`backend/pyproject.toml:5`), FastAPI ≥ 0.115, Uvicorn ≥ 0.30 with `[standard]` extras, SQLAlchemy 2.0 async with `asyncpg`, Alembic ≥ 1.13, Celery (Redis broker), structlog 24.1, httpx (30 s default timeout). Frontend: Next.js 15.2 on React 19.0, TypeScript 5.5, Tailwind 4, Zustand 5, TanStack Query 5.50, Axios 1.7, React Hook Form + Zod, Radix UI primitives, next-intl 3.20, Recharts, @dnd-kit, Vitest.

**Persistence.** PostgreSQL 16 (RDS `db.t3.medium`, 50 GB → 200 GB autoscale, multi-AZ, 14-day backup, deletion protection, `storage_encrypted = true` per `infra/terraform/main.tf:75`). Twenty-one ORM models share a `UUIDMixin + TimestampMixin + TenantMixin + SoftDeleteMixin` lineage. Indexes are composite and tenant-prefixed (e.g., `(company_id, status)`, `(company_id, phone)`). Redis 7.1 ElastiCache, two `cache.t3.medium` nodes, used for cache, Celery broker (db 1) and result backend (db 2). S3 (or MinIO in dev) bucket `kwgrowth` for media; **no CDN is configured**.

**Schema governance.** Alembic is wired in but the initial revision `907e034b43c9_initial_schema.py` is empty; in development the schema is materialised via `Base.metadata.create_all()` (`backend/app/main.py:37-43`). **A partner taking over operational ownership must generate and verify a baseline migration before the first production schema change** — this is the single highest-priority operational risk.

**Containerisation.** Multi-stage Dockerfile from `python:3.11-slim`, non-root `appuser`. `docker-compose.yml` provisions API, frontend, Nginx (production profile only), Postgres, Redis, MinIO, Celery worker, Celery beat — all with health checks.

**Cloud target.** AWS `me-south-1` (Bahrain) for GCC residency. Terraform provisions VPC (10.0.0.0/16, 2 AZ, NAT), RDS, ElastiCache, S3 (with a separate state bucket), IAM roles, ECS Fargate cluster `kwgrowth-production`, ALB with 80→443 redirect, CloudWatch logs/alarms (30-day retention), and auto-scaling on CPU/memory. State is held in `s3://kwgrowth-terraform-state` (encrypted).

**CI/CD.** GitHub Actions `.github/workflows/ci.yml` runs ruff + pytest (with Postgres + Redis service containers) and frontend lint/typecheck/build per PR. `deploy.yml` builds matrix images, pushes to ECR, runs Alembic via a migrate task, updates ECS services, then loops a smoke-test on `/health` and `GET /v1/payments/plans`. Authentication to AWS is via GitHub OIDC (`AWS_DEPLOY_ROLE_ARN`) — there are no long-lived AWS keys in the workflow.

---

## 5. Security Posture & Compliance Readiness

**Data protection.** TLS terminates at the ALB; intra-VPC traffic between ECS, RDS and ElastiCache is unencrypted in transit (no mTLS between services). RDS storage and S3 server-side encryption are on. A `core/encryption.py` Fernet helper exists but is **not applied uniformly to PII fields** (custom fields, notes); the integration partner should treat free-text fields as plaintext at rest.

**Vulnerability surface.**
- HS256 JWT (symmetric) — secret leakage forges all tenant tokens.
- CORS configured with `allow_methods=["*"], allow_headers=["*"]` (`backend/app/main.py:70`) — too permissive for a multi-origin enterprise deployment.
- Rate limiter exists (`backend/app/core/rate_limiter.py`, sliding window over Redis sorted sets) but is **not registered as global middleware** — endpoints are individually unprotected against floods.
- No CSRF tokens; reliance on SameSite cookie posture which is not explicitly configured.
- Twilio webhook `verify_webhook()` returns `True` unconditionally (`backend/app/services/whatsapp/twilio_provider.py`) — must be replaced before that fallback is enabled.
- Default development credentials in `docker-compose.yml` (`minioadmin/minioadmin`, `kwgrowth_dev`) — must be overridden in production.

**Access control.** RBAC with five roles and ≈30 permissions; enforcement is manual per endpoint and therefore audit-prone. ABAC is not implemented. Tenant isolation is application-enforced plus the Postgres GUC; **adding native RLS policies is recommended**.

**Compliance.** Eight CITRA-aligned checks are exposed via `GET /compliance/status` and a generated report via `GET /compliance/report`, including a data-residency attestation tied to the `me-south-1` deployment. Audit logs are immutable JSONB rows with composite indexes on `(company_id, created_at)` and `(entity_type, entity_id)` — adequate evidence for a CITRA audit.

---

## 6. Operational Resilience & Observability

**Telemetry.** Structlog produces JSON to stdout (CloudWatch in production), enriched per-request with `request_id`, `company_id`, `user_id`. Custom metrics in `backend/app/core/metrics.py` expose Prometheus counters/histograms (`http_requests_total`, `http_request_duration_seconds`, plus Celery task counts and DB query times). **No distributed tracing** (OpenTelemetry not integrated), **no Grafana dashboards provisioned**, and **Sentry is wired through config but not instantiated** in the reviewed code.

**Fault tolerance.** Celery tasks carry per-task retry policies; httpx clients use a 30 s timeout but no in-process retry. **No circuit breakers** are present — partners integrating to/from KWGE should implement breakers on their side for any synchronous coupling. Idempotency is correctly modelled on the inbound surfaces: WhatsApp `message.id`, Tap `charge_id`, and Aramex `tracking_number` are all unique-by-design and webhook handlers are upsert-shaped.

**Decoupling.** Eight named Celery queues separate workloads (messaging, automations, webhooks, analytics, imports, shipping, ai, default), so a slow Aramex API will not starve message delivery. Periodic work runs through Celery beat with a SQLite-backed schedule file (`backend/celerybeat-schedule`) — fine for a single-beat deployment but a single point of failure if duplicated.

---

## 7. Strategic Risk Assessment & Mitigation Roadmap

The risks below are ordered by integration impact, not by code severity.

**R1 — WebSocket fanout is not cluster-safe.** `ConnectionManager` (`backend/app/websocket/manager.py`) holds an in-process dict of sockets. Any horizontal scale-out (the very thing ECS auto-scaling provides) will silently drop real-time delivery for users connected to a different task. *Mitigation:* migrate to a Redis pub/sub bus or a hosted realtime service before exceeding one API task in production.

**R2 — Schema migrations are not source-controlled.** The Alembic baseline is empty; production schema is implicitly the ORM. *Mitigation:* `alembic revision --autogenerate` against a freshly created database, hand-review the diff, freeze, and gate CI on `alembic upgrade head` succeeding from an empty DB.

**R3 — Authentication is symmetric.** HS256 with a shared secret is a forgery risk and prevents the partner from offline verification. *Mitigation:* migrate to RS256 with a JWKS endpoint; rotate secret and revoke active refresh tokens during cutover.

**R4 — Three product surfaces are advertised but not functional.** Campaign send pipeline (gap #1), chatbot flow executor (partial), Twilio fallback (stub), and the Instagram/Facebook/Snapchat channel adapters. A partner promising omnichannel or broadcast in scope must treat these as build, not integrate. *Mitigation:* either descope at the contract or budget the 8–10 weeks indicated in `GAP_ANALYSIS.md`.

**R5 — Webhook signature verification is incomplete on Tap and Aramex inbound paths.** Treat any in-bound payment or shipment webhook as untrusted until signature checks are added.

**R6 — Rate limiting is configured but not enforced globally.** Public surfaces (`/auth/login`, `/webhooks/whatsapp`, `/payments/webhook`) are exposed to brute-force and replay floods. *Mitigation:* register `RateLimitMiddleware` ahead of the router, with stricter limits on auth and webhook paths.

**R7 — CORS is wildcard.** Tighten `allow_methods` and `allow_headers` to the explicit list the partner's origin uses.

**R8 — DB connection pool sized for development.** Pool size 20 + overflow 10 (`backend/app/config.py:31-32`) will saturate above ~50 concurrent users at typical query latency. Benchmark and re-tune.

**R9 — N+1 risk in CRM list endpoints.** Contacts-with-tags and conversations-with-last-message paths do not consistently use `selectinload`/`joinedload`. Profile under realistic tenant size before launch.

**R10 — No PII field-level encryption.** Custom fields and notes can hold sensitive data. Apply the existing Fernet helper to flagged columns.

**R11 — No CDN in front of S3.** Media latency to GCC mobile clients is bounded by direct S3 access; add CloudFront or equivalent.

**R12 — No integration SDKs.** Partners build raw HTTP clients today. *Mitigation:* generate an OpenAPI client (FastAPI emits the spec at `/openapi.json` automatically) for at least Python and TypeScript.

### Prescriptive Integration Posture

A recommended partner-side defensive pattern: (a) wrap every outbound call to KWGE in a circuit breaker with a 30 s rolling window; (b) treat WebSocket as best-effort and reconcile via REST polling for any business-critical state; (c) persist KWGE webhook payloads idempotently keyed by `message.id` / `charge_id` / `tracking_number`; (d) carry your own correlation ID into the `X-Request-ID` header so KWGE's structlog stream stitches against your own observability.

---

## 8. Critical Knowledge Gaps

The following are unresolved from the reviewed artefacts and materially affect integration planning. Each should be answered by the platform owner before a contract is signed.

1. **SLA targets.** No documented SLO for message-send latency, webhook-to-broadcast latency, or API availability. Without these, the partner cannot size its own breakers or alarms.
2. **Tenant scale envelope.** No load-test artefacts; the 100–500K-contact figure in `GAP_ANALYSIS.md` is unsupported by published benchmarks.
3. **Celery beat schedule contents.** The schedule file is binary; the actual list and cadence of periodic jobs is not visible in source.
4. **Outbound retry/backoff specifics.** Per-task retry policies are referenced but not consistently set in the reviewed task modules — true behaviour under Meta or Tap throttling is uncertain.
5. **Disaster recovery.** RPO/RTO, cross-region restore drill cadence, and ElastiCache snapshot policy are unstated.
6. **Secret rotation.** Mechanism for rotating `JWT_SECRET_KEY`, WhatsApp tokens, Tap keys and the database password is not described.
7. **Webhook signature schemes.** The exact HMAC scheme (or absence thereof) accepted by `/payments/webhook` and any future shipment webhook is not specified in code or docs.
8. **OpenAPI completeness.** FastAPI emits a spec automatically, but the degree to which response models are pinned (vs. `Any`) directly affects partner SDK quality and was not audited end-to-end.
9. **i18n contract for partner-facing strings.** Translation files exist (`frontend/src/i18n/`) but are not wired into pages (gap #12); RTL behaviour for an Arabic-first UI is therefore unverified.
10. **Data export format guarantees.** CSV column order and PDF schema are not versioned; any partner consuming `/export` outputs needs a stability commitment.

---

*End of blueprint.*
