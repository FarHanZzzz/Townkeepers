# CI/CD report

## Pipeline

File: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml). It runs on every push to `main` and on every pull request. One job, `gate`, runs on `ubuntu-latest` with a `postgres:17` service container.

| Step | Command | Gate source |
|---|---|---|
| Install from lock | `uv sync --locked` | TR section 7: install from the lock |
| Format check | `uv run ruff format --check .` | AGENTS.md section 5 |
| Lint | `uv run ruff check .` | AGENTS.md section 5 |
| System checks | `uv run python manage.py check` | AGENTS.md section 5 |
| Uncommitted migrations | `uv run python manage.py makemigrations --check --dry-run` | AGENTS.md section 5 |
| Migrate empty database | `uv run python manage.py migrate --noinput` | AGENTS.md section 5, TR section 7 |
| Browser install | `uv run playwright install --with-deps chromium` | Browser journey layer |
| All tests | `uv run pytest -ra --junitxml=test-results/junit.xml` | Unit, integration, race, contract, browser, acceptance |
| Unit-only coverage | `pytest tests/unit tests/contract --cov` | TR section 9: unit-only coverage reported separately |
| Requirement markers | `uv run python tools/check_req_markers.py` | TR section 7: reconcile acceptance markers to PRD IDs |
| Docstring inventory | `uv run interrogate -v apps/*/commands.py` (fail under 90%) | AGENTS.md section 7 |
| Sphinx | `uv run sphinx-build -W -b html docs/sphinx ...` | Documentation tool evidence |
| Deploy check | `manage.py check --deploy --fail-level WARNING` with production settings | AGENTS.md section 5 ("before release") |
| Artifacts | JUnit XML and coverage XML uploaded as `test-results` | Evidence for ASSESSMENT.md |

## Local runs (Windows 11, PostgreSQL 17.12, Python 3.13.7)

Each pipeline command was run locally before writing this report. Results:

| Command | Result |
|---|---|
| `ruff format --check .` | 145 files already formatted |
| `ruff check .` | All checks passed |
| `manage.py check` | No issues |
| `makemigrations --check --dry-run` | No changes detected |
| `migrate --noinput` | Applied (development and test databases) |
| `pytest` | 105 passed, 1 warning (from the pytest-playwright plugin's own fixture, not project code) |
| `tools/check_req_markers.py` | No unknown IDs. FR 45/91, UC 19/47, AC 12/20, NFR 10/22 and BR 4/12 referenced by tests |
| `interrogate` (command modules) | 100.0% (59/59) |
| `sphinx-build -W` | Built with no warnings |
| `check --deploy` (production settings, SMTP backend) | No issues. With `DEMO_AUTH=true` it fails with `townhall.E001` as intended |

## Not yet verified

- **The GitHub-hosted run.** The repository has not been pushed since these changes. After the first push, record the run URL and outcome here and in ASSESSMENT.md.
- **Deployment (CD).** No deployment target is defined yet. TR section 7 requires separate application and migration credentials, a backup before significant migrations, additive migrations before switching versions, and a staging rehearsal.
