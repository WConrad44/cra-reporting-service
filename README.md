# Team 21 CRA Article 14 Reporting Service

Team 21's implementation of the Pod K common CRA reporting service for ECE 30861.

The repository contains two FastAPI applications:

1. **System service** — `app.main:app`
2. **Automated tester** — `tester.main:app`

The authoritative Pod K requirements and interface are maintained with Team 17 in
`team17-ece30861/pod-k-shared`.

## Evaluation deployment

- System: https://cra-phase3.onrender.com
- Tester: https://cra-phase3-tester.onrender.com
- Hosting: Render, Virginia region, Python/FastAPI
- Health: `GET /health`

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
   -> SQLite evaluation database
```

See [docs/phase4-models.md](docs/phase4-models.md) for the delivered lifecycle, report-status,
draft-data, persistence and request-flow models.

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

The current Render evaluation service still uses SQLite. This is sufficient for the Phase 4
workflow, but durable restart persistence (REQ-18) is not yet claimed because Render's local
filesystem is not the final persistence design. PostgreSQL migration/restart validation and
REQ-17 performance validation are Phase 5 work.

The service does not submit reports directly to ENISA or a CSIRT, automatically determine
whether exploitation is active, scan products for vulnerabilities, or deploy fixes.
