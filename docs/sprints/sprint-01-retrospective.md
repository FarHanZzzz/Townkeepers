# Sprint 1 retrospective (template for the team)

Date: _to be filled_  ·  Attendees: _team members_  ·  Facilitator: _name_

## What went well

- _..._

## What did not go well

- _..._

## What we learned

Technical lessons already recorded in `docs/IMPLEMENTATION_CONTEXT.md` section 11:

- PostgreSQL rejects `FOR UPDATE` across a nullable outer join. Lock with `of=("self",)`.
- Transactional tests truncate migration-seeded rows. Use the `initial_policy` fixture.
- Browser tests must scroll the signature canvas into the viewport before drawing.

## Action items

| Action | Owner | Due |
|---|---|---|
| Push the branch and record the first GitHub Actions run in `docs/reports/CI_CD_REPORT.md` | _name_ | _date_ |
| Obtain the IUB hosted domain and Google OAuth client (PRD C.2) | _name_ | _date_ |
| Confirm the synthetic policy values with DoSA | _name_ | _date_ |
| Start Increment 3 with the AC-19 interval-boundary tests | _name_ | _date_ |
