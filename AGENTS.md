# Amader TOWNHALL coding standards

Place this file, `GRAND_PRD.md` and `TECHNICAL_REQUIREMENTS.md` in the repository root. These instructions apply to contributors and Cursor across the project. The PRD owns product behavior. The technical requirements own architecture and verification. Use the original FR, UC, BR, NFR and AC IDs in change descriptions and test metadata.

## 1. Work one behavior at a time

1. Read the relevant PRD feature, its referenced process and the applicable technical section. Identify the actor, scope, starting state, command, success result and failure path.
2. Write one failing test through the normal interface or domain command. Run it and confirm the failure is the missing behavior. Fix broken setup separately.
3. Implement the smallest production change that passes. Run the focused test and neighboring tests. Refactor while the suite is green.
4. Exercise the relevant failure, denial, retry, stale-data and concurrency paths. Add a regression test first for every confirmed defect.
5. In the change summary identify the requirement, affected entry points, tests actually run, migration effects and remaining verification. Report skipped or failing tests accurately.

**Cursor task example.** “Implement FR-MEM-08 for Advisor rejection using UC-22 and AC-16. Show the failing test first. Assert a required reason, one immutable decision, an EB in-app notification and an IUB email intent. The Head can see the decision in tracking and has no rejection email. Verify a second decision on the same version cannot commit.”

If an institutional value is missing, add a validated policy setting and an explicitly synthetic test value. Record the pending decision. Do not invent official lead times, domains, approval powers, default budgets or provider access.

## 2. Python, names and module ownership

- Use PEP 8 conventions, four spaces, snake_case for functions/modules, PascalCase for classes and UPPER_CASE for constants. Configure Ruff formatting and linting centrally. Pick one formatter and commit its settings with the dependency lock.
- Type new service functions, adapters and command inputs/outputs. Represent money with Decimal, instants with aware datetime values and controlled statuses with enums or Django TextChoices. Reserve free text for descriptions, reasons and typed designations.
- Name commands after the user action, such as `confirm_booking` and `reject_memo`. Keep views small. Parse forms and identify the actor in the view, enforce rules in the command, then render the result. Use one canonical function for each policy or calculation used in several places.
- Use Django ORM and Django migrations for authoritative records. Use FastAPI/Pydantic for internal assistance contracts. Keep provider payload types separate from domain models. Return only the fields the consumer needs.
- Prefer a direct function or a model constraint over a generic framework. Document a nonobvious invariant or lock order beside the code that enforces it. Use domain-specific exceptions handled at the boundary. Never discard an unexpected failure or report it as success.
- Keep Django templates accessible. Associate labels and errors with form fields, display status in text, preserve entered values on validation errors, and support keyboard access. Every visible action must have the same server-side permission check as a direct request.

## 3. Data and authorization

- Resolve records through scoped querysets. Pass the authenticated actor into commands. Check action, active profile, club or term, effective dates and record state. Recheck sensitive actions inside the transaction. Apply the same scope to counts, files, previews, exports and drill-downs.
- Validate at the form/API boundary, domain layer and database according to what each can enforce. A model choice list, hidden input or disabled button cannot establish permission.
- Protect immutable reviews, signed versions, release confirmations and approved amounts. Use linked revisions, adjustments or reversals. Never update historical evidence in place. Apply a correction once and keep its source and reason.
- Stage uploads privately, validate type/content and size, and keep a digest. Recheck permission on download. Keep tokens, institutional contacts, signatures and receipt data out of test fixtures, screenshots committed to Git, logs and prompts sent to external providers. Use synthetic examples.
- Run provider calls after the business transaction commits through a durable outbox. Use command keys for retryable writes, expected revisions for edits, and constraints for races. Never turn an email timeout into a repeated approval or expense.

## 4. Tests and fixtures

| Layer | Use it for | Required assertion |
|---|---|---|
| Pure Python | Policy dates, permitted transitions, variance, cash flow, priority explanation | Expected value and boundaries, including missing inputs and exact equality |
| Django request and command | Forms, scoped reads, state changes, redirects and error messages | Response plus persisted record, audit, permission and intended side effects |
| PostgreSQL transaction | Booking overlap, double decisions, corrections, idempotency | Independent transactions racing at a controlled barrier produce the permitted committed state |
| FastAPI contract | Input/output schemas, timeout, unsupported or stale candidate | Fake provider output stays advisory and the caller preserves the documented fallback |
| Browser journey | Sign-in, EB to Advisor to Head, booking, publishing, finance | Actual role can complete the workflow, sees the right status and can recover from a defined error |

Name tests after the outcome, such as `test_failed_reschedule_keeps_original_reservation`. Add a requirement marker or docstring containing the FR/AC IDs. Prefer explicit arrange, act and assert sections for stateful workflows. Use a controllable clock, synthetic identities for two clubs and at least two independent database connections for race tests. Use transaction-capable tests for commits and row locks. Mock external providers at their adapter boundary. Exercise the real ORM, constraints and transaction behavior on PostgreSQL. Reset FastAPI dependency overrides after each test.

## 5. Changes, migrations and review

- Commit schema migrations with the code that needs them. Include forward/backfill behavior for existing data. Prove an upgrade from the preceding schema for changes to identity, money, ownership or workflow state. Validate the data before tightening a constraint.
- Use environment-provided secrets. Commit example configuration with placeholders. Pin dependencies and review lock changes. Add one dependency only when its function and test coverage justify it.
- Keep changes focused. A PR description includes the FR/UC, intended behavior, tests run and any operator action. Document breaking contract changes and update both Django and FastAPI contract tests.
- Do not enable optional providers by default with production data. Exercise timeout, malformed response, duplicate delivery and manual fallback. Route institutional policy questions to the appropriate owner in PRD Appendix C.
- Before merging, run the repository’s equivalents of the commands below against a configured PostgreSQL test database. Configure these entry points when bootstrapping the repository. A green unit test alone cannot establish a booking concurrency guarantee.

```sh
ruff format --check .
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
pytest
```

Run `python manage.py check --deploy` with production-like settings before release. For changes touching reports, reconcile the worked finance fixture in the technical requirements. For changes touching one workflow, run its refusal and recovery scenarios as well as its successful path.

## 6. Requirements edits

Keep the eight named product features and the shared platform section. A new requirement under a feature needs a stable ID, a first-person user story and observable Success and Failure outcomes. Update the process and acceptance mapping, and specify the previous state after a failed action. Check the instructor’s Chapter 3 format whenever editing these sections. [Dhar Hobe formatting reference](https://github.com/JU-High-Fives/Dhar-Hobe/blob/main/resources/Dhar_Hobe___A_Bangladeshi_Renting_System%20%281%29.pdf)

Cursor recognizes root-level AGENTS.md project instructions. [Cursor rules documentation](https://cursor.com/docs/rules)

## 7. Course evidence for each change

Use the MVC responsibility map in docs/SDS.pdf. A Django view receives the request, a template renders presentation, and domain services and models enforce behavior. In public command docstrings identify actor scope, inputs, transaction effects, relevant errors and the FR. Document why stale or repeated commands are safe. Include a docstring-coverage inventory and a qualitative example for each major domain at release.

Version the source, editable documents, exported SRS/SDS and diagram sources in Git. Link the team card and FR/UC in the pull request. Request a human review through GitHub Pull Request Reviews, address findings and preserve the review trail. Link actual coverage and heuristic inspection evidence in the Wiki. Use ASSESSMENT.md and the repository PR template to collect the required evidence as the work happens.

## 8. Handover context

Before starting any task, read `docs/IMPLEMENTATION_CONTEXT.md`. It gives the document reading order, the module and command map, the state machines, the FR/UC/AC traceability status, the decisions log and the next increment to build. Update its traceability table and decisions log, and add evidence to `ASSESSMENT.md`, in the same change as the code.
