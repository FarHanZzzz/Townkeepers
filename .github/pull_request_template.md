## Requirement

- FR / UC / AC IDs:
- Team card:

## Intended behavior

<!-- Actor, scope, starting state, command, success result and failure path. -->

## Entry points affected

<!-- Views, commands, worker jobs, assistance endpoints, management commands. -->

## Tests actually run

<!-- Paste the commands and the summary lines. Report skipped or failing tests accurately. -->

- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run python manage.py check`
- [ ] `uv run python manage.py makemigrations --check --dry-run`
- [ ] `uv run python manage.py migrate --noinput`
- [ ] `uv run pytest`

## Migration effects

<!-- New tables, constraints, backfills, upgrade proof for identity/money/ownership/workflow changes. -->

## Operator action and remaining verification

<!-- Settings, secrets, policy values, pending live verification (PRD Appendix C.2). -->

## Evidence

- [ ] `ASSESSMENT.md` updated
- [ ] `docs/IMPLEMENTATION_CONTEXT.md` traceability and decisions log updated
- [ ] Human review requested through GitHub Pull Request Reviews
