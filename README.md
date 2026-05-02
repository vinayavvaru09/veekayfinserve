# Veekay Finserve — Insurance Renewal Automation System

## Architecture

```
backend/          FastAPI API + Celery tasks
  app/
    api/v1/       REST endpoints (policies, providers, notices, templates, logs)
    core/         Config, security (JWT + credential encryption)
    db/           SQLAlchemy sessions
    models/       ORM models
    schemas/      Pydantic schemas
    tasks/        Celery tasks (scheduler, portal, notifications, alerts)
  alembic/        Database migrations

frontend/         Next.js 14 dashboard
  app/
    auth/         Google SSO login + callback
    dashboard/    Notices, Policies, Providers, Templates, Logs pages
  components/     Shared UI + layout components
  lib/            Supabase client, API client, utilities
  types/          TypeScript types
```

## Services

| Service | Purpose |
|---|---|
| FastAPI (uvicorn) | REST API |
| Celery worker | Portal automation, notifications |
| Celery Beat | Daily 07:00 IST scheduled job |
| Redis | Celery broker + result backend |
| PostgreSQL (Supabase) | Database + auth |
| Next.js | Internal dashboard |

## Local Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Fill in .env values

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app.celery_app worker --loglevel=info

# Start Celery Beat (separate terminal)
celery -A app.tasks.celery_app.celery_app beat --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Fill in .env.local values

npm run dev
```

## Deployment (Railway)

1. Create a Railway project with 5 services: `api`, `worker`, `beat`, `dashboard`, `redis` (plugin).
2. Point each service to its Dockerfile (see `railway.toml` comments).
3. Set environment variables from `backend/.env.example` on all backend services.
4. Set `NEXT_PUBLIC_*` variables on the `dashboard` service.
5. Run migrations: `railway run --service api -- alembic upgrade head`
6. Enable Google OAuth in Supabase Auth settings and add the dashboard URL as a redirect URL.

## Supabase Setup

1. Create a new Supabase project.
2. Enable Google OAuth under Authentication → Providers.
3. Add `https://your-dashboard.railway.app/auth/callback` as an allowed redirect URL.
4. Copy `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_JWT_SECRET` to backend `.env`.

## Portal Automation

The base Playwright automation in `app/tasks/portal.py` implements a generic login flow.
For each insurer portal, create a provider-specific adapter in `app/services/portal_adapters/`
that handles the exact DOM selectors and login flow for that portal.

When CAPTCHA or OTP is detected, the task sets the notice to `pending_manual_upload`
and emails agents. Agents upload the PDF via the dashboard.

## Gupshup WhatsApp Setup

1. Register at [gupshup.io](https://www.gupshup.io) and create a WhatsApp app.
2. Submit English and Telugu message templates for Meta approval (24–72 hours).
3. Set `GUPSHUP_API_KEY`, `GUPSHUP_APP_NAME`, `GUPSHUP_SOURCE_NUMBER` in `.env`.

## Credential Encryption

Portal credentials are encrypted with Fernet (AES-128-CBC) before storage.
Generate a key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set the output as `CREDENTIAL_ENCRYPTION_KEY` in `.env`.
