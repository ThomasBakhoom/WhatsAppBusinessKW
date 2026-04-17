# Kuwait WhatsApp Growth Engine

Enterprise WhatsApp CRM platform for the Kuwait market. Multi-tenant SaaS with Kuwaiti dialect AI, K-Net payments, and CITRA-aligned compliance.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery, Redis
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS v4, shadcn/ui (RTL)
- **Database**: PostgreSQL 16 with Row-Level Security (RLS) for multi-tenancy
- **WhatsApp**: Cloud API (primary), Twilio (fallback) via provider abstraction
- **Payments**: Tap Payments (K-Net, Visa, Mastercard) — KWD uses `DECIMAL(12,3)`
- **Storage**: MinIO (dev) / AWS S3 (prod)
- **Deploy**: Docker Compose (dev), AWS ECS Fargate or Railway (prod)

## Quick Start (Local Dev)

```bash
# Start all services
cd docker
cp .env.docker.example .env.docker  # fill in dev secrets
docker compose --env-file .env.docker up -d

# Apply migrations
docker compose --env-file .env.docker exec api alembic -c alembic/alembic.ini upgrade head

# Seed demo data (optional)
docker compose --env-file .env.docker exec api python -m scripts.seed_demo

# Login at http://localhost:3000
# Email: owner@albaraka.kw
# Password: Demo123!
```

## Services

| Service | URL (local) | Purpose |
|---|---|---|
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Frontend | http://localhost:3000 | Next.js dashboard |
| Postgres | localhost:5432 | Tenant-isolated via RLS |
| Redis | localhost:6379 | Cache + Celery + WebSocket pub/sub |
| MinIO | http://localhost:9001 | S3-compatible storage |

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment guides:

- **Railway** (recommended for quick testing) — see `DEPLOYMENT.md#railway`
- **AWS ECS Fargate** (production-grade) — see `infra/terraform/`
- **Fly.io + Neon + Upstash** (fully free tier)

## Features

| Module | Capability |
|---|---|
| Inbox | Real-time WhatsApp conversations, smart agent routing |
| Contacts | CRM with tags, custom fields, CSV import/export |
| Pipeline | Kanban sales board with drag-and-drop |
| Campaigns | Bulk WhatsApp broadcasts (80 msgs/sec rate limit) |
| Automations | Trigger-based workflow engine |
| Chatbots | Visual flow builder with payment link nodes |
| Landing Pages | Drag-and-drop builder with WhatsApp CTA |
| Analytics | Dashboard, pipeline, team, campaign stats |
| Compliance | CITRA-aligned, RLS-enforced, audit logged |

## Security

- JWT authentication (15-min access, 7-day refresh)
- bcrypt password hashing (12 rounds)
- PostgreSQL Row-Level Security under non-superuser runtime role (`app_user`)
- Tap webhook HMAC-SHA256 signature validation
- Redis sliding-window rate limiting per route + per client
- Audit logging on every mutation (contacts, deals, conversations, subscriptions, payments, tags, custom fields, shipping, channels, chatbots, auth)
- Automated 365-day data retention purge
- Production secret validation at startup (refuses to boot with dev placeholders)

## Tests

```bash
cd docker
docker compose --env-file .env.docker exec api python -m pytest tests/ -q
# 117 tests covering RLS, audit, rate limiting, all major endpoints
```

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) — Deploy to Railway or AWS
- [docs/USER_MANUAL.pdf](docs/USER_MANUAL.pdf) — Bilingual (EN + AR) user guide
- [docs/USER_MANUAL_EN.md](docs/USER_MANUAL_EN.md) — English manual (markdown)
- [docs/USER_MANUAL_AR.md](docs/USER_MANUAL_AR.md) — Arabic manual (markdown)

## License

Proprietary. All rights reserved.
