# Amader TOWNHALL

Club administration for Independent University, Bangladesh (IUB). One record follows an event from its first memo draft through Faculty Advisor confirmation, DoSA Head approval, venue booking, publication, expenses and EB handover. The prototype uses the IUB Programming Club.

Built with Python, Django (server-rendered templates), a private FastAPI assistance service and PostgreSQL.

## Team name: Townkeepers

| Name | ID | Initials |
|---|---|---|
| _Member name_ | _ID_ | _XX_ |
| _Member name_ | _ID_ | _XX_ |
| _Member name_ | _ID_ | _XX_ |
| _Member name_ | _ID_ | _XX_ |

## Documents

| Document | Purpose |
|---|---|
| [GRAND_PRD.md](GRAND_PRD.md) | Product behavior: features, FR/UC/AC identifiers, business rules |
| [TECHNICAL_REQUIREMENTS.md](TECHNICAL_REQUIREMENTS.md) | Architecture, contracts, transactions and release verification |
| [AGENTS.md](AGENTS.md) | Coding standards for contributors and Cursor |
| [docs/IMPLEMENTATION_CONTEXT.md](docs/IMPLEMENTATION_CONTEXT.md) | Handover: module map, state machines, traceability status, next steps |
| [ASSESSMENT.md](ASSESSMENT.md) | Course evidence: test results, coverage, heuristics, docstring inventory |
| [docs/SRS.pdf](docs/SRS.pdf), [docs/SDS.pdf](docs/SDS.pdf) | Revised SRS and software design specification |
| [docs/Use_Case_Narratives.pdf](docs/Use_Case_Narratives.pdf) | 47 revised use-case narratives |
| [docs/design/](docs/design/) | Use-case, DFD and state diagrams |
| [docs/reports/](docs/reports/) | TDD report and CI/CD report |
| [docs/sprints/](docs/sprints/) | Sprint planning and retrospectives |
| [docs/sphinx/](docs/sphinx/) | API documentation generated from docstrings |

# How to use

## 1. Clone the project

```sh
git config --global user.name <github_username>
git config --global user.email <github_email>
git clone https://github.com/FarHanZzzz/Townkeepers.git
cd Townkeepers
```

## 2. Install the tools

- Python 3.13 and [uv](https://docs.astral.sh/uv/).
- PostgreSQL 17. On Windows: `winget install PostgreSQL.PostgreSQL.17`. With Docker: `docker compose up -d db`.

## 3. Create the database

Run in `psql` as the PostgreSQL superuser (replace the password):

```sql
CREATE ROLE townhall LOGIN PASSWORD 'change-me' CREATEDB;
CREATE DATABASE townhall OWNER townhall;
\c townhall
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

The test database `test_townhall` is created by the test runner. The `townhall` role needs `CREATEDB`; the migrations create the extensions in the test database.

## 4. Configure and run

```sh
copy .env.example .env          # then edit DATABASE_URL and secrets
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo        # synthetic Programming Club and Science Club
uv run python manage.py runserver        # http://127.0.0.1:8000/
```

Optional processes, each in its own terminal:

```sh
uv run python manage.py run_worker                       # IUB email and other durable jobs
uv run uvicorn assistance.app:app --port 8001            # private assistance API
```

With `DEMO_AUTH=true` in development, `/dev/login/` lists the seeded synthetic personas. Live sign-in uses IUB Google at `/auth/google/start`.

# How to develop

## 1. Create a branch

```sh
git checkout -b <feature>/<FR-ID>-short-name
```

## 2. Make changes test-first

Follow [AGENTS.md](AGENTS.md): read the PRD feature, write one failing test with a `@pytest.mark.req("FR-...", "AC-...")` marker, implement the smallest change, then add denial, stale, retry and concurrency tests.

```sh
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run pytest
```

## 3. Run the full gate before pushing

```sh
uv run ruff format --check .
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run pytest
```

## 4. Commit and push

```sh
git add .
git commit -m "FR-MEM-08: reject memo at Advisor stage"
git push origin <branch>
```

## 5. Check CI

Open the repository's **Actions** tab, select the pipeline run and inspect the `gate` job. CI runs the same gate against a PostgreSQL service.

## 6. Open a pull request

Open a pull request into `main`. The [template](.github/pull_request_template.md) asks for the FR/UC, behavior, tests run, migration effects and operator action.

## 7. Review and merge

Request a review through GitHub Pull Request Reviews, address findings and merge after approval.

## 8. Update your local copy

```sh
git checkout main
git pull origin main
git branch -d <branch>
```
