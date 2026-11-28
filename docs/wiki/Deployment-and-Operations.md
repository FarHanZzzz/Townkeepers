# Deployment and Operations

This page covers deployment expectations, release gates, runtime operations, and incident handling for Amader TOWNHALL.

## Environments

| Environment | Purpose | Data | Notes |
|---|---|---|---|
| Local dev | Developer workflow | Synthetic | `DEMO_AUTH` may be enabled. |
| CI | Automated quality gate | Synthetic/test | PostgreSQL service; no real providers. |
| Staging | Pre-release verification | Synthetic/anonymized | Production-like settings; no real institutional secrets in logs. |
| Production | Live IUB use | Real institutional data | Strict security, backups, monitoring, approved providers only. |

## Release Gates

Before production release, the project should pass:

1. **Code quality gate**: Ruff format/check, Django check, migrations check, tests green.
2. **Migration safety**: forward/backfill plan, rollback/restore consideration, upgrade from previous schema.
3. **Security checks**: `manage.py check --deploy` with production settings, secret scan, dependency review.
4. **Operational readiness**: health probes, logs/metrics, alerting, worker supervision.
5. **Recovery drills**: backup/restore rehearsal (NFR-REL-02).
6. **Performance/resilience**: load/concurrency tests for booking and key workflows.
7. **Accessibility**: WCAG 2.2 AA review and keyboard/screen-reader checks.

## Deployment Checklist

- [ ] Confirm environment variables and secrets are set in secret manager/platform config.
- [ ] Run migrations during deploy window: `python manage.py migrate --noinput`.
- [ ] Collect static files if applicable: `python manage.py collectstatic --noinput`.
- [ ] Restart web app and worker processes.
- [ ] Verify health endpoints/readiness.
- [ ] Smoke test sign-in, dashboard, memo list, event calendar, file download permissions.
- [ ] Check worker is consuming jobs and no error spike in logs.

## Runtime Processes

| Process | Command | Purpose |
|---|---|---|
| Web app | Django WSGI/ASGI server (prod-grade) | Serves UI/API endpoints. |
| Worker | `python manage.py run_worker` | Processes durable jobs (email/outbox). |
| Assistance API | `uvicorn assistance.app:app` | Advisory scheduling/OCR contracts. |

Run worker and assistance as supervised services (systemd, container orchestrator, or platform process manager).

## Monitoring and Alerts

Monitor at minimum:

- **Availability:** web health, DB connectivity, worker heartbeat.
- **Errors:** 5xx rate, domain error spikes, unhandled exceptions.
- **Jobs:** backlog age, retry count, failed/uncertain jobs.
- **Security:** auth failures, permission-denied anomalies, suspicious upload/download patterns.
- **Performance:** slow queries, request latency, booking confirmation contention.
- **Dependencies:** email/provider timeout/failure rates.

Alert on sustained failure conditions, not single transient blips.

## Backups and Restore

- **Database:** automated regular backups; encrypt at rest; test restore regularly.
- **Private files:** backup object/storage volume with access controls.
- **Restore rehearsal:** periodically restore to staging and verify critical workflows (sign-in, memo history, booking, finance reconciliation).
- **RPO/RTO:** define and document with institutional owners.

## Incident Response

1. **Detect** — alert, user report, or monitoring anomaly.
2. **Triage** — severity, impacted users, data integrity risk.
3. **Contain** — disable affected feature/provider, pause worker if causing harm, block abusive traffic.
4. **Mitigate** — rollback deploy, hotfix, or apply safe config change.
5. **Recover** — restore service, replay safe jobs, verify integrity.
6. **Postmortem** — root cause, timeline, corrective actions, tests/alerts added.

## Rollback Strategy

- Prefer **forward fixes** for schema/data migrations where possible.
- Keep migrations backward-compatible during rollout when feasible.
- For risky changes, deploy in phases: schema, dual-write/read compatibility, code switch, cleanup.
- Never rollback by deleting audit/financial history; use compensating records where needed.