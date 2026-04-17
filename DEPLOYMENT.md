# Deployment Guide

Step-by-step deploy to Railway. Total time: ~20 minutes.

## Railway Deployment

### Why Railway
- GitHub integration: auto-deploys on push
- Built-in Postgres + Redis (managed)
- Free subdomain with HTTPS (required for WhatsApp webhooks)
- $5/month free credit (enough for a small testing workload)

### Prerequisites
- GitHub repo with code pushed (see push instructions below)
- Railway account: <https://railway.app> — sign in with GitHub
- Credit card on file (no charges on free tier unless you exceed $5/mo)

---

## Step 1: Push Code to GitHub

```bash
cd "D:/Work/Kuwait WhatsApp Growth Engine/App"
git init
git branch -M main
git add .
git commit -m "Initial commit: Kuwait WhatsApp Growth Engine"
git remote add origin https://github.com/ThomasBakhoom/WhatsAppBusinessKW.git
git push -u origin main
```

If the remote has any existing commits you'll need `git pull --rebase origin main` first.

---

## Step 2: Create Railway Project

1. Go to <https://railway.app/new>
2. Click **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub
4. Select `ThomasBakhoom/WhatsAppBusinessKW`
5. Railway creates an **empty project** — we'll add services next

---

## Step 3: Add Postgres + Redis

Inside the project:

1. Click **"+ New"** → **Database** → **Postgres**
   - Railway provisions a managed Postgres 16 instance
   - It auto-generates `DATABASE_URL` as a reference variable
2. Click **"+ New"** → **Database** → **Redis**
   - Auto-generates `REDIS_URL`

---

## Step 4: Deploy the API Service

1. Click **"+ New"** → **GitHub Repo** → select `WhatsAppBusinessKW` → **Add service**
2. Rename the service to **`api`**
3. Click **Settings** on the api service:
   - **Root Directory**: `backend`
   - **Watch Paths**: `backend/**`
   - **Build Command**: (leave empty — uses Dockerfile)
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Click **Variables** tab, add:
   ```
   APP_ENV=production
   APP_DEBUG=false
   APP_SECRET_KEY=<generate — see below>
   JWT_SECRET_KEY=<generate — see below>
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   MIGRATION_DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   CELERY_BROKER_URL=${{Redis.REDIS_URL}}
   CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
   APP_DOMAIN=https://${{RAILWAY_PUBLIC_DOMAIN}}
   ALLOWED_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}}
   WHATSAPP_VERIFY_TOKEN=<generate — any strong string>
   ```
5. Click **Settings** → **Networking** → **Generate Domain** (gives you `api-xxx.up.railway.app`)

**Generate secrets** in a terminal:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"  # run 3 times for 3 different secrets
```

Use one for `APP_SECRET_KEY`, one for `JWT_SECRET_KEY`, one for `WHATSAPP_VERIFY_TOKEN`.

---

## Step 5: Apply Migrations

In the Railway dashboard, on the `api` service → **Settings** → **Deploy Triggers** → **Run Command**:

```
alembic -c alembic/alembic.ini upgrade head
```

Click **Run Now**. Check the logs; you should see all 10 migrations applied.

---

## Step 6: Seed Roles + Plans

Same panel, run:

```
python -m scripts.seed
```

(This seeds the 5 roles and 3 pricing plans. Do NOT run `seed_demo` in production.)

---

## Step 7: Deploy Celery Worker

1. Click **"+ New"** → **GitHub Repo** → same repo → **Add service**
2. Rename to **`worker`**
3. Settings:
   - **Root Directory**: `backend`
   - **Start Command**: `celery -A app.tasks.celery_app worker --loglevel=info -Q default,messaging,automations,webhooks,analytics,imports,shipping,ai`
4. Variables: copy all from `api` service (Railway has a "copy variables" button on the Variables tab)

---

## Step 8: Deploy Celery Beat

Same pattern, one more service:
- Name: `beat`
- Start Command: `celery -A app.tasks.celery_app beat --loglevel=info`
- Copy variables from `api`

---

## Step 9: Deploy Frontend

1. **"+ New"** → **GitHub Repo** → same repo → **Add service**
2. Rename to **`frontend`**
3. Settings:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm ci && npm run build`
   - **Start Command**: `npm start`
4. Variables:
   ```
   NEXT_PUBLIC_API_URL=https://<api-service-domain>/v1
   NEXT_PUBLIC_WS_URL=wss://<api-service-domain>/ws
   NODE_ENV=production
   PORT=3000
   ```
   Replace `<api-service-domain>` with the domain generated in Step 4.
5. **Generate Domain** for this service too.

---

## Step 10: Connect WhatsApp Cloud API

1. Go to <https://business.facebook.com> → your Business → **WhatsApp > Getting Started**
2. Get:
   - **Phone Number ID** → add as `WHATSAPP_CLOUD_API_PHONE_NUMBER_ID` in `api` service variables
   - **Access Token** (temporary, 24h) or permanent System User token → `WHATSAPP_CLOUD_API_TOKEN`
3. In Meta App dashboard → **WhatsApp > Configuration**:
   - **Webhook URL**: `https://<api-service-domain>/v1/webhooks/whatsapp`
   - **Verify Token**: same value you set in `WHATSAPP_VERIFY_TOKEN`
   - Click **Verify and Save** — Meta will GET your endpoint with the verify token
4. **Subscribe** to `messages` webhook field

---

## Step 11: Register + Test

1. Visit `https://<frontend-domain>/register`
2. Create your company account
3. Go to **Settings > Channels > Connect WhatsApp** and confirm the phone number shows up
4. Send a WhatsApp message to your Business number from another phone
5. It should appear in the Inbox in real-time (via WebSocket)

---

## Environment Variables Cheat Sheet

**Required for `api`, `worker`, `beat`:**
| Variable | Value |
|---|---|
| `APP_ENV` | `production` |
| `APP_DEBUG` | `false` |
| `APP_SECRET_KEY` | 64-char random string |
| `JWT_SECRET_KEY` | 64-char random string (different from above) |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` reference |
| `MIGRATION_DATABASE_URL` | Same as `DATABASE_URL` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` reference |
| `CELERY_BROKER_URL` | Same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | Same as `REDIS_URL` |
| `ALLOWED_ORIGINS` | Frontend domain |
| `APP_DOMAIN` | Frontend domain |
| `WHATSAPP_VERIFY_TOKEN` | Random string — also set in Meta webhook config |
| `WHATSAPP_CLOUD_API_TOKEN` | From Meta Business |
| `WHATSAPP_CLOUD_API_PHONE_NUMBER_ID` | From Meta Business |

**Optional but recommended:**
| Variable | Source |
|---|---|
| `SENTRY_DSN` | sentry.io free tier |
| `TAP_SECRET_KEY` | tap.company dashboard (sandbox: `sk_test_*`) |
| `TAP_WEBHOOK_SECRET` | Tap dashboard → Webhooks |
| `ANTHROPIC_API_KEY` | console.anthropic.com |

**For frontend:**
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<api-domain>/v1` |
| `NEXT_PUBLIC_WS_URL` | `wss://<api-domain>/ws` |

---

## Troubleshooting

### API won't start: "Refusing to start in production with insecure config"
`APP_SECRET_KEY` or `JWT_SECRET_KEY` is empty, too short (<32 chars), or uses a dev placeholder. Generate strong ones with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

### WhatsApp webhook verification fails
- The `WHATSAPP_VERIFY_TOKEN` in Railway must EXACTLY match the Verify Token in Meta App dashboard
- The webhook URL must be `https://` (not `http://`)

### DB migrations failed
Check the `api` service logs for the migration command output. If `app_user` role doesn't exist yet (Railway's Postgres doesn't have our init.sql), run this in Railway's Postgres query console:
```sql
CREATE ROLE app_user LOGIN PASSWORD 'strong-pw-here';
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```
Then update the `api` service's `DATABASE_URL` to use `app_user:strong-pw-here` instead of the default user.

### Frontend returns 502
Next.js sometimes needs 2 minutes to warm up. Check the `frontend` service logs — look for "Ready in XXXs".

### Celery worker not processing tasks
Make sure `CELERY_BROKER_URL` points to the same Redis as the API. Check `worker` logs for `ready` message.

---

## Cost Estimate

| Resource | Monthly cost |
|---|---|
| Postgres (shared) | ~$2 |
| Redis (shared) | ~$1 |
| API service (~512MB, low traffic) | ~$1 |
| Worker service | ~$0.50 |
| Beat service | ~$0.20 |
| Frontend (~256MB) | ~$0.30 |
| **Total** | **~$5/mo** (covered by free credit) |

If you exceed $5/mo, Railway charges per-usage. Monitor via the **Usage** tab.
