# Contributing

Thanks for contributing to Amader TOWNHALL. This project prioritizes correctness, auditability, accessibility, and requirement traceability.

## Before You Start

1. Read [AGENTS.md](../../AGENTS.md).
2. Read [Implementation Context](../IMPLEMENTATION_CONTEXT.md).
3. Identify the relevant FR/UC/AC/BR/NFR IDs in [GRAND_PRD.md](../../GRAND_PRD.md).
4. Check [TECHNICAL_REQUIREMENTS.md](../../TECHNICAL_REQUIREMENTS.md) for architectural/verification rules.

## Development Workflow

1. **Pick one behavior.** Keep PRs focused.
2. **Write a failing test first** (or add a failing case) through the normal interface/domain command.
3. **Implement the smallest change** to pass.
4. **Add denial/failure/retry/stale/concurrency cases** where relevant.
5. **Update docs/evidence** in the same change: traceability, assessment, decisions as needed.

## Branch and Commit

```powershell
git checkout -b <type>/<FR-ID>-short-name
# examples:
# feat/FR-EVT-10-calendar-filter
# fix/FR-MEM-08-advisor-rejection-reason
```

Commit messages should be clear and scoped. Include requirement IDs when applicable.

## Pull Request Checklist

- [ ] Behavior matches PRD and technical requirements.
- [ ] Tests added/updated; all required tests pass.
- [ ] No secrets, personal data, or debug artifacts committed.
- [ ] Migrations included (if needed) and safe.
- [ ] Audit/permission/idempotency/stale-state implications handled.
- [ ] Accessibility considered (labels, focus, keyboard, status text).
- [ ] Docs updated (README/wiki/implementation context/assessment as needed).
- [ ] PR description includes: FR/UC, behavior, tests run, migration effects, remaining verification.

## Code Standards

- **Python:** PEP 8, 4-space indent, Ruff format/lint clean.
- **Types:** type hints for new service/command/adapter code.
- **Domain writes:** use command protocol; no ad-hoc state mutation in views.
- **Money/time:** `Decimal` for money, aware datetimes for instants, Asia/Dhaka for local display.
- **Errors:** domain-specific exceptions; never swallow unexpected failures.
- **Templates:** accessible, labeled, keyboard operable, status text not color-only.

## Testing Expectations

| Change type | Expected tests |
|---|---|
| Pure policy/calculation | Unit tests with boundaries/invalid cases. |
| View/command workflow | Integration/request tests for success + denial + stale/retry. |
| DB invariants/races | PostgreSQL transaction/race tests. |
| Provider contract | FastAPI contract tests with fake provider/fallback. |
| Critical user journey | Playwright/browser test when feasible. |

Run the full quality gate before PR:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run pytest
```

## Documentation and Evidence

- Update [ASSESSMENT.md](../../ASSESSMENT.md) with tests actually run.
- Update [Implementation Context](../IMPLEMENTATION_CONTEXT.md) traceability/decisions when relevant.
- For UI changes, include screenshots and note accessibility checks performed.
- For requirement edits, follow PRD formatting/ID rules and update mappings.