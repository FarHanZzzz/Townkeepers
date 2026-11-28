# Amader TOWNHALL

Club administration for Independent University, Bangladesh (IUB). One record follows an event from its first memo draft through Faculty Advisor confirmation, DoSA Head approval, venue booking, publication, expenses and EB handover. The prototype uses the IUB Programming Club.

Built with Python, Django (server-rendered templates), a private FastAPI assistance service and PostgreSQL.

## Team name: Townkeepers

| Name | ID | Initials | Role & Primary Responsibility |
|---|---|---|---|
| **Farhan Sadeque** | 2331178 | FS | Team Leader & Software Development |
| **Fabiha Raidha Khan** | 2211214 | FRK | Requirements & Documentation Lead |
| **Abid Abdullah Fardin** | 2420958 | AAF | Application Development & Implementation |
| **Ayon Abdullah** | 2331581 | AA | System Design & Documentation Support |

## Course Submission Chapters (`FinalVersion_Documents/`)

The full coursework documentation and submission deliverables are indexed below:

| Chapter | Title & Scope | Primary Deliverable |
|---|---|---|
| **Chapter 01** | Software Requirements Specification | [SRS_Final_Reviewed.pdf](FinalVersion_Documents/Chapter01_SRS/SRS_Final_Reviewed.pdf) |
| **Chapter 02** | Software Design Specification (SDS) | • [DFD Level 0 (System Context)](FinalVersion_Documents/Chapter02_SDS/DFD/DFD_Level-0%20Final.pdf)<br>• [Use Case Diagrams (47 Use Cases)](FinalVersion_Documents/Chapter02_SDS/Individual%20Use%20Case%20Diagrams/)<br>• [State Diagrams (6 Core Lifecycles)](FinalVersion_Documents/Chapter02_SDS/Individual%20State%20Diagrams/)<br>• [Use Case Narratives Final](FinalVersion_Documents/Chapter02_SDS/Use%20Case%20Narratives/Use_Case_Narratives%20Final.pdf) |
| **Chapter 03** | Project Collaboration & Agile Process | [Trello and Discord Evidence.pdf](FinalVersion_Documents/Chapter03_TrelloDiscordEvidence/Trello%20and%20Discord%20Evidence.pdf) |
| **Chapter 04** | Architectural Pattern & MVC Responsibility | [Architecture Pattern_Final.pdf](FinalVersion_Documents/Chapter04_ArchitecturalPattern/Architecture%20Pattern_Final.pdf) |
| **Chapter 05** | Coding Standards & Technical Specifications | [Coding Standards_Final.pdf](FinalVersion_Documents/Chapter05_CodingStandards/Coding%20Standards_Final.pdf) |
| **Chapter 07** | UI Design & Workflow Visual Hierarchy | [UI Design_Final.pdf](FinalVersion_Documents/Chapter07_UIDesign/UI%20Design_Final.pdf) |
| **Chapter 08** | Nielsen Usability Heuristics Evaluation | [UI Heuristics_Final.pdf](FinalVersion_Documents/Chapter08_NielsenHeuristics/UI%20Heuristics_Final.pdf) |
| **Chapter 09** | Code Review, Static Analysis & Lint Findings | [Code Review_Final.pdf](FinalVersion_Documents/Chapter09_CodeReviewToolsandFinding/Code%20Review_Final.pdf) |
| **Chapter 10** | Git Workflow, Branching & Merge Strategy | [Git Usage_Final.pdf](FinalVersion_Documents/Chapter10_GitUsage/Git%20Usage_Final.pdf) |
| **Chapter 11** | Test-Driven Development & Unit Testing Report | [Unit Testing_Final.pdf](FinalVersion_Documents/Chapter11_UnitTesting/Unit%20Testing_Final.pdf) |
| **Chapter 12** | Individual Team Member Contributions | [Member Contribution.pdf](FinalVersion_Documents/Chapter12_TeamContribution/Member%20Contribution.pdf) |

## Core Repository Engineering Documents

| Document | Purpose |
|---|---|
| [GRAND_PRD.md](GRAND_PRD.md) | Authoritative product behavior: 8 core features, FR/UC/AC identifiers, business rules |
| [TECHNICAL_REQUIREMENTS.md](TECHNICAL_REQUIREMENTS.md) | Technical architecture, data invariants, concurrency locks, API contracts, release gates |
| [AGENTS.md](AGENTS.md) | Coding standards, test-first conventions, scoping rules, and PR requirements |
| [docs/IMPLEMENTATION_CONTEXT.md](docs/IMPLEMENTATION_CONTEXT.md) | Handover context: module map, state machines, decisions log, next implementation increments |
| [ASSESSMENT.md](ASSESSMENT.md) | Verification evidence: test pass counts, coverage metrics, heuristics checks, docstring inventory |

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
