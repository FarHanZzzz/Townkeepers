# Configuration

This page documents runtime configuration, environment variables, and policy values for Amader TOWNHALL.

## Environment Variables

Use `.env.example` as the baseline. Values below are representative; verify against the current `.env.example` in the repo.

| Variable | Required | Purpose | Example / Notes |
|---|---:|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django cryptographic secret | Long random value. Never commit. |
| `DJANGO_DEBUG` | Dev | Debug mode | `true` in local dev only. |
| `DJANGO_ALLOWED_HOSTS` | Yes (prod) | Host allowlist | Comma-separated hostnames. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Yes (prod) | CSRF trusted origins | Include scheme, e.g. `https://app.example.edu`. |
| `DATABASE_URL` | Yes | PostgreSQL connection | `postgres://user:pass@host:5432/townhall` |
| `TEST_DATABASE_NAME` | Test | Test DB name override | Optional depending on setup. |
| `DEMO_AUTH` | Dev | Enable demo login | `true` only in development. |
| `IUB_ALLOWED_DOMAINS` | Prod auth | Allowed Google sign-in domains | Institutional domains only. |
| `GOOGLE_CLIENT_ID` | Prod auth | Google OIDC client ID | From institutional Google config. |
| `GOOGLE_CLIENT_SECRET` | Prod auth | Google OIDC secret | Secret; never commit. |
| `EMAIL_BACKEND` | Yes | Django email backend | Console in dev, SMTP/provider in prod. |
| `DEFAULT_FROM_EMAIL` | Yes | Sender identity | Approved institutional sender. |
| `SITE_BASE_URL` | Yes | Absolute base URL | Used in links/emails/exports. |
| `MAX_UPLOAD_BYTES` | Yes | Upload size limit | Enforce in validation and settings. |
| `ASSISTANCE_URL` | Optional | FastAPI assistance base URL | Private internal endpoint. |
| `ASSISTANCE_SERVICE_TOKEN` | Optional | Assistance auth token | Secret; service-to-service only. |
| `ASSISTANCE_TIMEOUT_SECONDS` | Optional | Assistance call timeout | Keep short; fallback to manual flow. |

## Configuration Rules

- **Secrets in environment, not code.** Do not commit `.env`, tokens, credentials, or private keys.
- **Production-safe defaults.** `DEBUG=false`, secure cookies, HTTPS, strict hosts/CSRF origins.
- **Demo isolation.** Demo personas and demo login must be disabled/unavailable in production.
- **Provider timeouts/fallbacks.** AI/OCR/email/publishing failures must degrade safely.

## Policy Values (Admin-configurable)

Policy values are stored as versioned policy records (`PolicyVersion`) and applied by effective date. Examples:

| Policy | Purpose | Current state |
|---|---|---|
| Standard lead days | Memo submission lead time for normal events | Configured; confirm institutional value. |
| Big-event lead months | Lead time for Big events | Configured; confirm institutional value. |
| Approval buffer days | Default approval deadline offset | Synthetic until confirmed. |
| Review window days | Review SLA/window | Synthetic until confirmed. |
| Working days | Campus working-day definition | Synthetic until confirmed. |
| Venue restrictions | Restricted hours/closures | Admin-managed; synthetic catalogue in dev. |

## Synthetic / Pending Institutional Values

The prototype includes synthetic values for safe development. These must be replaced/confirmed before live deployment:

- IUB allowed domains and Google OAuth credentials
- Official sender address / SMTP provider
- Venue capacities, hours, buffers, closure calendars
- Finance evidence rules, conversion evidence, reporting periods
- External publishing destinations and credentials
- OCR/AI provider approval and data handling terms

Track pending values in [Implementation Context](../IMPLEMENTATION_CONTEXT.md#10-pending-institutional-decisions-and-synthetic-values).

## Static/Media/File Configuration

- **Static files:** collected via Django static pipeline; `static_v` cache-busting used where applicable.
- **Private media:** stored under private media root, not public static serving.
- **File validation:** allowlist type, size limit, digest, permission-checked download endpoints.
- **Generated exports:** A4 memo previews/PDFs served through authorized endpoints.

## Feature Flags / Operational Switches

If adding feature flags, document:

- name and default
- scope (global/tenant/role)
- rollout plan
- rollback plan
- owner and removal date

Avoid permanent “temporary” flags.