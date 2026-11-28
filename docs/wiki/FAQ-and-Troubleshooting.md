# FAQ and Troubleshooting

## General

### Where is the canonical product behavior?
`GRAND_PRD.md` owns product behavior. `TECHNICAL_REQUIREMENTS.md` owns architecture/verification. `AGENTS.md` owns coding practice.

### Where should I start when continuing development?
Read `docs/IMPLEMENTATION_CONTEXT.md` first, then AGENTS/PRD/technical requirements as needed.

### Is demo data real?
No. Demo/seed data is synthetic. Do not use real institutional data in tests, fixtures, screenshots, or prompts.

## Setup & Runtime

### `/dev/login/` is missing or forbidden
- Ensure `DEMO_AUTH=true` in `.env`.
- Confirm you are not running with production settings; production rejects demo auth.

### Database migrations fail with GiST/exclusion constraint errors
- Ensure PostgreSQL has `btree_gist` extension:
  ```sql
  CREATE EXTENSION IF NOT EXISTS btree_gist;
  ```
- Rerun migrations.

### I get 403/404 unexpectedly
- 403 means authenticated but not permitted for that action/object.
- 404 may mean object does not exist **or is out of scope** (intentionally concealed).
- Check active profile, grants, club/term assignment, effective dates, and object state.

### A form says “stale revision” / “changed since you opened it”
- Another action updated the record. Refresh, review the current state, and retry with the updated revision/token.

## Development & Tests

### `uv` is not recognized
- Install uv and add to PATH, or use `.venv\Scripts\python.exe -m ...`.

### Playwright browser tests fail
- Install browser once:
  ```powershell
  uv run playwright install chromium
  ```

### Ruff fails after edits
- Run:
  ```powershell
  uv run ruff format .
  uv run ruff check . --fix
  ```
- Manually resolve remaining issues (unused imports, complexity, unsafe fixes).

### Tests pass locally but fail in CI
- Check PostgreSQL service availability/extensions.
- Ensure migrations are committed.
- Confirm timezone/clock assumptions use controllable clock fixtures.
- Verify no environment-dependent paths or missing env vars.

## Features / Behavior

### Why does AI/OCR not automatically finalize data?
By design. AI/OCR outputs are advisory/unverified until a human confirms through the normal workflow. This prevents silent authoritative changes.

### Why do I see “Synthetic” labels?
Prototype uses synthetic venues/policies/data where institutional values are not confirmed. These must be replaced before live deployment.

### Why can’t I see Venues/Finance/Reports as a non-DoSA persona?
Navigation is role-scoped. Some admin/oversight surfaces are intentionally DoSA-only in the current UI; server-side permissions still apply independently.

### How do I report a bug?
Include: steps to reproduce, expected vs actual, role/persona, environment, screenshots/logs (redacted), and requirement ID if known. Use the issue/report workflow in the repo.