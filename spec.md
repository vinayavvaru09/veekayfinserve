# Insurance Renewal Automation System — MVP Spec

**Client:** Veekay Finserve LLP  
**Scope:** MVP — Renewal Process Only

---

## 1. Problem Statement

Veekay Finserve manually tracks insurance policy renewals across 6–15 providers and 2,000–10,000 active policies. The current process requires staff to identify expiring policies, log into each insurer portal, download renewal notices, and contact customers — all manually. This spec defines an automated system that handles scheduling, portal document retrieval (with a human-in-the-loop fallback for CAPTCHA/OTP), customer notifications via WhatsApp and email, and an internal dashboard for tracking and management.

---

## 2. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Strong Playwright/Celery ecosystem; async-friendly |
| Task Queue | Celery + Redis | Reliable scheduled jobs and async task execution |
| Database | PostgreSQL (via Supabase) | Managed Postgres with built-in auth and storage |
| Document Storage | PostgreSQL bytea / Supabase Storage | PDFs stored as binary blobs per requirement |
| Portal Automation | Playwright (Python) | Best-in-class headless browser; handles complex portals |
| WhatsApp | Gupshup | India-focused, pre-approved template support, competitive pricing |
| Email | Resend | Simple API, reliable deliverability |
| Dashboard Frontend | Next.js 14 (App Router) | Modern React framework; pairs well with Supabase Auth |
| Auth | Supabase Auth (Google SSO) | Native Google OAuth; no custom auth code needed |
| Deployment | Railway | Managed containers; supports Celery workers + Redis + web |
| Secrets | Railway environment variables + Supabase Vault | Portal credentials never stored in plaintext |

---

## 3. Data Models

### 3.1 Policy

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `customer_name` | TEXT NOT NULL | |
| `policy_number` | TEXT UNIQUE NOT NULL | |
| `date_of_birth` | DATE | |
| `phone_number` | TEXT | Required for WhatsApp |
| `email` | TEXT | Required for email |
| `type_of_policy` | ENUM(Motor, Life, Medical) | |
| `insurance_provider_id` | UUID FK → InsuranceProvider | |
| `policy_expiry_date` | DATE NOT NULL | |
| `hold_date` | DATE NULLABLE | |
| `renewed_date` | DATE NULLABLE | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### 3.2 InsuranceProvider

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `provider_name` | TEXT UNIQUE NOT NULL | |
| `portal_url` | TEXT NOT NULL | |
| `login_credentials` | JSONB (encrypted) | Stored via Supabase Vault / encrypted at rest |
| `additional_auth_details` | JSONB NULLABLE | OTP config, security questions, etc. |
| `created_at` | TIMESTAMPTZ | |

### 3.3 RenewalNotice

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `policy_id` | UUID FK → Policy | |
| `policy_number` | TEXT NOT NULL | Denormalized for query performance |
| `policy_expiry_date` | DATE NOT NULL | Denormalized |
| `customer_name` | TEXT NOT NULL | |
| `date_of_birth` | DATE | |
| `phone_number` | TEXT | |
| `email` | TEXT | |
| `type_of_policy` | ENUM | |
| `insurance_provider_id` | UUID FK | |
| `creation_date` | TIMESTAMPTZ NOT NULL | |
| `renewal_document` | BYTEA NULLABLE | PDF binary; null until uploaded |
| `document_filename` | TEXT NULLABLE | Original filename |
| `status` | ENUM(pending_automation, pending_manual_upload, completed, failed) | |
| `source` | ENUM(automated, manual_upload, reused) | How the document was obtained |
| `hold_date` | DATE NULLABLE | Snapshot at time of notice creation |
| `renewed_date` | DATE NULLABLE | Snapshot at time of notice creation |
| UNIQUE | `(policy_number, policy_expiry_date)` | Idempotency constraint |

### 3.4 NotificationLog

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `renewal_notice_id` | UUID FK → RenewalNotice | |
| `policy_number` | TEXT NOT NULL | |
| `channel` | ENUM(whatsapp, email) | |
| `language` | ENUM(en, te) NULLABLE | WhatsApp only |
| `days_to_expiry` | INT NOT NULL | Reminder day trigger (e.g. 30, 15, 1) |
| `status` | ENUM(sent, failed, skipped) | |
| `sent_at` | TIMESTAMPTZ NULLABLE | |
| `error_message` | TEXT NULLABLE | |
| UNIQUE | `(policy_number, channel, days_to_expiry)` | Prevents duplicate notifications |

### 3.5 ProcessingLog

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `run_date` | DATE NOT NULL | |
| `policy_id` | UUID FK NULLABLE | |
| `policy_number` | TEXT | |
| `action` | TEXT | e.g. "skipped_missing_contact", "portal_failed", "notice_reused" |
| `detail` | TEXT NULLABLE | Error message or reason |
| `created_at` | TIMESTAMPTZ | |

### 3.6 MessageTemplate

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `channel` | ENUM(whatsapp, email) | |
| `language` | ENUM(en, te) NULLABLE | |
| `template_key` | TEXT UNIQUE | e.g. "whatsapp_renewal_en" |
| `subject` | TEXT NULLABLE | Email only |
| `body` | TEXT NOT NULL | Supports `{{customer_name}}`, `{{policy_number}}`, `{{policy_expiry_date}}` placeholders |
| `updated_at` | TIMESTAMPTZ | |

---

## 4. Scheduled Job — Daily at 07:00 AM IST

### 4.1 Policy Selection

For each policy in the database:

1. Compute `days_to_expiry = policy_expiry_date - current_date`
2. Skip if `days_to_expiry` ∉ `{30, 25, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1}`
3. Skip if `hold_date` is not null AND `hold_date >= current_date`
4. Skip if `renewed_date` is not null AND `renewed_date <= current_date` → **already renewed**
5. Skip if `phone_number` is null/empty AND `email` is null/empty → log to ProcessingLog
6. Eligible policies proceed to renewal notice handling

### 4.2 Renewal Notice Handling

**Step 1 — Check for reusable notice:**
- Query RenewalNotice for `policy_number = X AND policy_expiry_date = Y AND status = 'completed'`
- If found AND `creation_date >= (policy_expiry_date - 31 days)`: mark `source = reused`, skip generation

**Step 2 — Generate new notice (if no reusable notice):**
- Check if a `pending_automation` or `pending_manual_upload` notice already exists for `(policy_number, policy_expiry_date)` → if so, skip creation (idempotent)
- Create RenewalNotice record with `status = pending_automation`
- Dispatch Celery task: `generate_renewal_notice(renewal_notice_id)`

### 4.3 Portal Automation Task

1. Load provider credentials from Supabase Vault
2. Launch Playwright browser session (headless)
3. Navigate to `portal_url`, attempt login
4. Search by `policy_number`, locate renewal notice, download PDF
5. **On success:** store PDF in `renewal_document`, set `status = completed`, `source = automated`
6. **On CAPTCHA/OTP block or any error:**
   - Retry up to 3 times (exponential backoff: 1 min, 5 min, 15 min)
   - After 3 failures: set `status = pending_manual_upload`, trigger agent alert (see §7.2)
   - Log failure to ProcessingLog

### 4.4 Manual Upload Fallback

- Dashboard displays all `pending_manual_upload` notices prominently
- Agent downloads PDF from portal manually and uploads via dashboard
- On upload: set `status = completed`, `source = manual_upload`
- Triggers notification dispatch (§5)

---

## 5. Customer Notifications

### 5.1 Trigger

Notifications are dispatched when a RenewalNotice transitions to `status = completed` (automated or manual upload).

### 5.2 Idempotency Check

Before sending, query NotificationLog for `(policy_number, channel, days_to_expiry)`. If a `sent` record exists, skip.

### 5.3 WhatsApp (via Gupshup)

- Send in **English** and **Telugu** (two separate messages)
- Use pre-approved Gupshup templates
- Attach RenewalDocument PDF
- Template variables: `{{customer_name}}`, `{{policy_number}}`, `{{policy_expiry_date}}`
- On failure: retry 3x, log to NotificationLog with `status = failed`

### 5.4 Email (via Resend)

- Subject and body from MessageTemplate (`template_key = 'email_renewal'`)
- Attach RenewalDocument PDF
- Template variables: `{{customer_name}}`, `{{policy_number}}`, `{{policy_expiry_date}}`
- On failure: retry 3x, log to NotificationLog with `status = failed`

### 5.5 Skip Conditions

- Missing `phone_number` → skip WhatsApp, log as skipped
- Missing `email` → skip email, log as skipped
- Both missing → skip all, log to ProcessingLog

---

## 6. Internal Dashboard

### 6.1 Authentication

- Google SSO via Supabase Auth
- Admin manually provisions user accounts (no self-registration)
- Single role for MVP: `agent`

### 6.2 Policy Management

- **List view:** paginated table of all policies
- **Create/Edit policy:** form with all Policy fields
- **Filters:** TypeOfPolicy, InsuranceProvider, PolicyExpiryDate range
- **Inline status:** shows linked RenewalNotice status if any

### 6.3 Renewal Notice Dashboard

**Filters:**
- Policy Expiry Date (date range)
- Insurance Provider
- TypeOfPolicy
- Notice Status (pending_automation, pending_manual_upload, completed, failed)

**Display columns:**
- CustomerName
- PolicyNumber
- PolicyExpiryDate
- InsuranceProvider
- TypeOfPolicy
- Notice Status
- Document (download/view button, disabled if not yet available)

**Actions per row:**
- **View/Download** renewal document (if `status = completed`)
- **Upload document** (if `status = pending_manual_upload`)
- **Regenerate** — manually trigger portal automation for any policy (creates new Celery task; respects idempotency by voiding previous failed notice)

### 6.4 Processing Log View

- Read-only table of all ProcessingLog entries
- Filters: run_date range, action type, policy_number search

### 6.5 Provider Management

- CRUD for InsuranceProvider records
- Credentials stored encrypted; displayed masked in UI

### 6.6 Message Template Management

- Edit body/subject for each MessageTemplate
- Preview with sample variable substitution

---

## 7. Agent Alerts

### 7.1 Daily Summary Email

Sent to all agents at ~07:30 AM IST (after job completes):

- Total policies processed
- Notices generated (automated vs reused vs pending manual)
- Notifications sent (WhatsApp + email counts)
- Failures requiring manual action
- Skipped records count

### 7.2 Failure Alert Email

Triggered immediately when a portal automation task exhausts all 3 retries:

- PolicyNumber
- InsuranceProvider
- Failure reason
- Link to dashboard record

---

## 8. Validation Rules

| Condition | Action |
|---|---|
| Missing `phone_number` AND `email` | Skip policy; log to ProcessingLog |
| `days_to_expiry` not in trigger set | Skip silently |
| `hold_date >= current_date` | Skip; log |
| `renewed_date` is set and in the past | Skip; log |
| Duplicate `(policy_number, policy_expiry_date)` notice | Skip generation (idempotent) |
| Duplicate `(policy_number, channel, days_to_expiry)` notification | Skip send (idempotent) |

---

## 9. Security

- Portal credentials stored in Supabase Vault (AES-256 encrypted); never logged or exposed in API responses
- All API endpoints require authenticated session (Supabase JWT)
- Renewal documents served via signed URLs or streamed server-side; never exposed as public URLs
- Environment variables (API keys, DB URL) managed via Railway secrets

---

## 10. Assumptions

- Policy data is entered and maintained by agents via the dashboard
- Insurance provider portals are accessible from the deployment server's IP
- Renewal notice PDFs can be downloaded after searching by PolicyNumber
- System clock is IST (UTC+5:30); all scheduling uses IST
- Gupshup WhatsApp templates for English and Telugu will be pre-approved before go-live
- PDF attachments via WhatsApp are supported by the chosen Gupshup plan

---

## 11. Out of Scope (MVP)

- Policy comparison or recommendation features
- Customer-facing portal or self-service
- Payment processing for renewals
- SMS channel
- Mobile app
- Multi-tenancy (single company only)

---

## 12. Implementation Plan

1. **Project scaffold** — FastAPI app, Next.js dashboard, Celery + Redis, Supabase project, Railway config
2. **Database schema** — Create all tables with constraints, indexes, and RLS policies in Supabase
3. **Auth** — Supabase Google SSO integration; protect all API routes and dashboard pages
4. **Policy CRUD API + Dashboard UI** — Policy list, create, edit, filters
5. **InsuranceProvider CRUD** — API + dashboard UI with encrypted credential storage
6. **Scheduled job (Celery Beat)** — Policy selection logic, eligibility checks, notice creation
7. **Portal automation (Playwright)** — Per-provider automation scripts with retry logic and CAPTCHA fallback
8. **Manual upload flow** — Dashboard upload UI + API endpoint; triggers notification dispatch
9. **WhatsApp notifications (Gupshup)** — Template integration, bilingual send, idempotency
10. **Email notifications (Resend)** — Template integration, attachment, idempotency
11. **Renewal Notice dashboard** — Filters, status display, download, upload, regenerate actions
12. **Agent alerts** — Daily summary email + failure alert email
13. **Processing Log view** — Read-only dashboard page
14. **Message Template management** — Dashboard UI for editing templates
15. **End-to-end testing** — Scheduled job simulation, notification idempotency, portal fallback flow
