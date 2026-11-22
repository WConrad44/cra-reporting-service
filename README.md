# Team 21 CRA Article 14 Reporting Service

Team 21's implementation of the Pod K common CRA reporting service for ECE 30861.

The repository contains two FastAPI applications:

1. **System service** — `app.main:app`
2. **Automated tester** — `tester.main:app`

The authoritative Pod K requirements and interface are maintained with Team 17 in
`team17-ece30861/pod-k-shared`.

## Evaluation deployment

- System: https://team21-cra-reporting-service.onrender.com
- Tester: https://cra-phase3-tester.onrender.com
- Hosting: Render, Virginia region, Python/FastAPI
- Health: `GET /health`
- Registry **Access/Run Notes:** [How to open the deployed API and run the tester](docs/registry-access-run-notes.md) — direct links to /docs, authorization guidance, and Swagger/terminal examples.

The Render services are linked to this GitHub repository. A push/merge to `main` triggers
a new deployment. The public service can scale down when idle, so warm it with `GET /health`
before timed tests.

## Delivered through Phase 4

### Phase 3 foundation

- REQ-01 ticket intake
- REQ-02 actively-exploited triage
- REQ-03 non-reportable/invalid triage
- REQ-04 CRA deadline calculation
- REQ-12 common error behavior
- REQ-13 RFC 3339 / UTC handling
- REQ-14 bearer authentication and actor identification
- REQ-16 deterministic reset and test clock

### Phase 4 reporting workflow

- REQ-05 live report status, including `submitted` and `submitted_late`
- REQ-06 full ticket updates and immediate deadline recalculation
- REQ-07 early-warning, notification, final-report and user-advisory drafts
- REQ-08 ordered report-submission recording with locked content snapshots
- REQ-09 closure after all three Article 14 reports are recorded
- REQ-10 filtered and deterministic ticket listing
- REQ-11 append-only per-ticket audit history
- REQ-15 reporter confidentiality outside the single-ticket response

Phase 4 also incorporates the Pod K clarifications agreed with Team 17: irrelevant
`aware_at` values on non-reportable triage are accepted and ignored; list ties use
`received_at` then ID; no-op edits create no audit entry; future fix/corrective-measure
times are rejected; and an explicit `unknown` value is accepted where Member State
information is not yet known.

## Current architecture

```text
HTTPS request
   -> FastAPI route
   -> bearer / X-Actor checks
   -> Pydantic validation
   -> ticket + reporting rules
   -> SQLAlchemy
   -> Render PostgreSQL (canonical deployment; SQLite for local/CI checks)
```

See [Phase 5 as-delivered system models](docs/phase5-models.md) for the current PostgreSQL
architecture and data-flow diagrams. The previous [Phase 4 models](docs/phase4-models.md)
document the unchanged ticket lifecycle, report-status, and draft-data rules.

## API workflow

A normal reportable incident follows:

```text
POST /tickets
  -> POST /tickets/{id}/triage
  -> PATCH /tickets/{id} as investigation data arrives
  -> GET /tickets/{id}/reports/early_warning
  -> POST /tickets/{id}/reports/early_warning/submission
  -> GET /tickets/{id}/reports/notification
  -> POST /tickets/{id}/reports/notification/submission
  -> GET /tickets/{id}/reports/final_report
  -> POST /tickets/{id}/reports/final_report/submission
  -> POST /tickets/{id}/close
```

Supporting reads include filtered `GET /tickets`, `GET /tickets/{id}`,
`GET /tickets/{id}/audit`, and the `user_advisory` draft.

## Authentication

`GET /health` is public. Project API operations require:

```text
Authorization: Bearer <private token>
```

Ticket-changing project operations additionally require:

```text
X-Actor: <person or client name>
```

The separate course-wide `POST /test/setup` endpoint does not require `X-Actor`.
Tokens are configured as Render environment variables and are never committed.

## Test controls

The evaluation deployment keeps:

- `POST /test/reset`
- `GET /test/clock`
- `PUT /test/clock`
- `DELETE /test/clock`
- course `POST /test/setup`
- course `GET /test/report?session_id=...`

Only one destructive test suite should run against a deployment at a time.

## Running locally

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export API_TOKEN=dev-token
export DATABASE_URL=sqlite:///./cra.db
python3 -m uvicorn app.main:app --reload
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:API_TOKEN="dev-token"
$env:DATABASE_URL="sqlite:///./cra.db"
py -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the local Swagger interface.

## Automated validation

Run the Team 21 regression suite:

```bash
python3 -m pytest -q
ruff check app tester tests
```

GitHub Actions runs dependency validation, Python compilation, Ruff and pytest on pushes
and pull requests to `main`.

The shared Model D E1-E8 deadline suite was independently checked against the Phase 2
rules and reproduced by the Team 21 evaluation deployment (8/8).

## Automated tester

The tester exposes:

- `POST /test/setup`
- `POST /test/run`
- `GET /test/report?session_id=...`

It selects a target-specific bearer credential from `TARGET_TOKENS_JSON`; this is how
Team 21's tester authenticates to Team 17 without putting credentials in source code or
the class registry.

## Persistence and Phase 5 limitations

The canonical Render evaluation service uses a managed PostgreSQL database via the
internal `DATABASE_URL` setting; SQLite remains available for local development and CI.
Phase 5 runs demonstrate 1,000-ticket AC-18 performance, 18/18 deployed self-acceptance,
and reciprocal cross-team acceptance. The AC-19 prepare/verify script compares tickets,
locked report content, and audit history across a web-service restart/redeploy; the operator
must retain the intervening Render event as external evidence. In-memory fixed test-clock
and tester sessions are not durable.

The service does not submit reports directly to ENISA or a CSIRT, automatically determine
whether exploitation is active, scan products for vulnerabilities, or deploy fixes.


## Phase 5 implementation

See [Phase 5 operations and evidence](docs/phase5-operations.md) for the Render PostgreSQL setup, deployed/cross-team checks, and AC-19 procedure. The [evidence ledger](docs/phase5-results.md) records actual passing and failing results. Team 21's [JSON-file intake channel](docs/phase5-intake.md) supports researcher ticket submissions through the common API.


Phase 5 hardens the delivered reporting workflow rather than changing its CRA lifecycle.
The implementation adds:

- AC-18 / REQ-17 performance validation: 1,000 stored tickets followed by 200
  sequential mixed requests with a measured p95 target of at most one second.
- Session source-line coverage returned by the system through
  `GET /test/report?session_id=...`.
- Phase 5 `coverage.model` in Team 21 self-test reports, mapped to
  `docs/phase5-design.md`; model coverage is omitted for cross-team runs.
- Revised course test-interface error bodies using nonempty `message` and `source`.
- PostgreSQL compatibility and CI execution of the complete regression suite against
  PostgreSQL.
- `scripts/ac19_restart_check.py` for the owning-team AC-19 restart-persistence
  demonstration.

### Render PostgreSQL setup required for REQ-18

The code is ready for PostgreSQL, but the database itself must be provisioned in Render.
For the canonical system service, `team21-cra-reporting-service`:

1. Create a Render PostgreSQL database in the same region as the service (Virginia).
2. Copy/use its internal database URL.
3. Add or replace the system service environment variable `DATABASE_URL` with that URL.
   The application normalizes Render's `postgresql://` URL to the psycopg 3 SQLAlchemy
   dialect automatically.
4. Redeploy the system and run the full functional suite.
5. Run the AC-19 demonstration:

```bash
export CRA_BASE_URL=https://team21-cra-reporting-service.onrender.com
export CRA_API_TOKEN='<Team 21 token>'
python scripts/ac19_restart_check.py prepare
# Restart/redeploy only the system service in Render.
python scripts/ac19_restart_check.py verify
```

The state file produced by the helper contains test data only and must not contain the API
token. Do not run `/test/reset` between the prepare and verify steps.

### Phase 5 testing-interface coverage

A Team 21 self-test report contains `code`, `component`, `system`, and `model`
coverage. Cross-team reports intentionally omit `model`. Component coverage remains
unavailable until Pod K publishes a shared component list and exercise rules; the revised
course interface permits unavailable measures to use null counts with a nonempty basis.
