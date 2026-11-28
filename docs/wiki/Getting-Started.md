# Getting Started

This guide gets a developer running Amader TOWNHALL locally for development and demo.

## Prerequisites

| Tool | Recommended | Notes |
|---|---:|---|
| Python | 3.13+ | Project uses modern Django/FastAPI tooling. |
| uv | latest | Used for dependency management and commands. |
| PostgreSQL | 17 | Required for real constraints/race behavior. |
| Git | latest | Standard workflow. |
| Playwright Chromium | optional | Needed only for browser tests. |

## 1. Clone and configure

```powershell
git clone https://github.com/FarHanZzzz/Townkeepers.git
cd Townkeepers
copy .env.example .env
```

Edit `.env` with at least:

- `DATABASE_URL` — PostgreSQL connection string
- `DJANGO_SECRET_KEY` — local dev secret
- `DEMO_AUTH=true` — enables `/dev/login/` demo personas (development only)

> **Do not enable `DEMO_AUTH` in production.** Production settings reject it.

## 2. Create database

Create role and database in PostgreSQL (example from README):

```sql
CREATE ROLE townhall LOGIN PASSWORD 'change-me' CREATEDB;
CREATE DATABASE townhall OWNER townhall;
\c townhall
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

`btree_gist` is required for booking overlap exclusion constraints.

## 3. Install dependencies and migrate

```powershell
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
```

`seed_demo` creates synthetic clubs, personas, and sample workflow data.

## 4. Run the app

```powershell
uv run python manage.py runserver
```

Open `http://127.0.0.1:8000/`. With `DEMO_AUTH=true`, use `/dev/login/` to sign in as a demo persona.

## 5. Optional services

Run in separate terminals as needed:

```powershell
# Durable job worker (email/outbox jobs)
uv run python manage.py run_worker

# Private assistance API (FastAPI)
uv run uvicorn assistance.app:app --port 8001
```

## 6. Quality checks

Run the standard gate before pushing:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run pytest
```

Useful additional checks:

```powershell
uv run python tools/check_req_markers.py
uv run interrogate apps/*/commands.py
uv run sphinx-build -W -b html docs/sphinx docs/sphinx/_build/html
uv run playwright install chromium   # one-time for browser tests
```

## 7. Demo walkthrough

1. Sign in as a synthetic President at `/dev/login/`.
2. Create an event and start an event-permission memo.
3. Send memo to Faculty Advisor.
4. Sign in as Advisor; confirm or reject with reason.
5. Sign in as DoSA Head; approve/reject as appropriate.
6. Preview/export A4 memo output.

## Common Local Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `uv` not found | uv not installed/on PATH | Install uv or use `.venv\Scripts\python.exe` directly. |
| DB connection errors | Bad `DATABASE_URL` / Postgres not running | Verify PostgreSQL service, credentials, DB name. |
| Migration/constraint errors on booking | Missing `btree_gist` | Create extension in DB; rerun migrations. |
| `/dev/login/` unavailable | `DEMO_AUTH` off or production settings | Set `DEMO_AUTH=true` in dev only. |
| Playwright tests fail | Browsers not installed | Run `uv run playwright install chromium`. |