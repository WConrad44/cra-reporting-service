# Phase 5 operations and acceptance evidence — Team 21

This runbook accompanies [Phase 5 design requirements](phase5-design.md). Use only the Pod K evaluation deployments; all test suites can reset the entire target database.

## Registered addresses

| Service | Base URL |
|---|---|
| Team 21 system | https://team21-cra-reporting-service.onrender.com |
| Team 21 tester | https://cra-phase3-tester.onrender.com |
| Team 17 system | https://team17-prod-7zneiwx4ba-uc.a.run.app |
| Team 17 tester | https://team17-prod-7zneiwx4ba-uc.a.run.app/tester |

Use base URLs without a trailing `/test` for the course registry. The Team 21 URLs were already entered in the registry, as confirmed in the November 22 screenshot.

**Access/Run Notes for the registry:** [Browser access, authentication, and running the hosted tester](registry-access-run-notes.md). Do not open the system API base URL as though it were a public website; use `/docs` or public `/health`. The tester exposes `POST /test/setup` and `POST /test/run` through its `/docs` page. GitHub access is not required for either deployed endpoint.

## Secure configuration

1. In Render, open the *canonical* **team21-cra-reporting-service** (not the older **cra-reporting-service** deployment). Confirm `DATABASE_URL` points to the **team21-cra-postgres** Render PostgreSQL instance via its *internal* PostgreSQL connection URL. The service and database must be in the same Render region; do not paste the database URL into GitHub or test reports.
2. Keep `API_TOKEN` configured on the Team 21 system. The deployed tester must have `TARGET_TOKENS_JSON` with the Team 21 and Team 17 system base URLs mapped to their private bearer tokens. In the tester, `TEAM21_SYSTEM_URL` should equal the registered Team 21 system URL.
3. Add a **GitHub Actions repository secret** named `TEAM17_TESTER_TOKEN` for the token required to call Team 17's protected `/tester/test/*` endpoints. This is needed for the reverse-direction GitHub workflow. Do not commit, log, or place any token in the registry.
4. Confirm `GET /health` and `GET /openapi.json` on both Team 21 services. The code advertises version `0.5.0`.

The existence of a Render PostgreSQL instance alone does *not* prove that the service uses it. Verify the service's `DATABASE_URL` environment variable in Render (without disclosing its value) and perform AC-19.

## Validation sequence

The GitHub deployed-self, cross-team and independent Phase 5 workflows are
**manual-only** because every run resets its target's ticket data. Before running
any of them, coordinate with Team 17 and other Team 21 operators.

For the latest verified and incomplete acceptance results, see the
[Phase 5 evidence ledger](phase5-results.md). For an independent load test,
select the `performance` option of the
`Independent Phase 5 acceptance evidence (Team 17 runner)` GitHub workflow.
This workflow requires a GitHub Actions secret named `TEAM21_API_TOKEN`.
Its `malformed` and `full-functional` options provide additional independent
evidence. Save every generated artifact, including failure reports.


Do not run suites against the same target simultaneously: they call `POST /test/reset` and permanently delete its data. The GitHub deployed-self and cross-team workflows share a concurrency group to serialize runs within Team 21's repository, but coordinate separately with Team 17 and instructors.

1. Merge the code changes and wait for the canonical system and tester to deploy.
2. Run GitHub **CI** and confirm both the SQLite and PostgreSQL jobs pass. CI checks are necessary but do not prove Render persistence or deployed performance.
3. Run **Deployed self-validation**. Require exactly one passing result for each `AC-01` through `AC-18`, plus `coverage.code`, `coverage.component`, `coverage.system`, and self-test-only `coverage.model`. Save the uploaded `deployed-self-report` artifact.
4. Run **Cross-team validation** (Team 21 tester → Team 17 system, then Team 17 tester → Team 21 system). Require a valid complete report with no failing results in either direction. Save the uploaded `cross-team-reports` artifact. A green workflow with `continue-on-error` is *not* pass evidence; the hardened workflows fail when assertions fail.
5. Check `AC-18` in the self-test: it loads 1,000 tickets and sends 200 sequential mixed requests. The 95th percentile must be ≤ 1.000 seconds and all measured requests must return the expected success status. Save the reported p95, request count, target URL, date, and result.
6. Demonstrate `AC-19` by recording data, restarting *only* the canonical Render web service, and comparing ticket, report and audit data. See below.
7. After evidence has been recorded, clean up test state only when no other run is active (`POST /test/reset`; `DELETE /test/clock`).

## AC-19 restart procedure

Use a terminal with the repository's dependencies installed (`pip install -r requirements.txt`). Set the token as a private environment variable; never include its literal value in commands or logs.

```bash
export CRA_BASE_URL=https://team21-cra-reporting-service.onrender.com
export CRA_API_TOKEN='<set privately>'
python scripts/ac19_restart_check.py prepare
```

The `prepare` command resets the evaluation data and creates a ticket, recorded early-warning report, and audit entries. It stores an expected data snapshot in `ac19-state.json`.

Restart or redeploy **team21-cra-reporting-service** in the Render dashboard; do **not** delete/recreate its PostgreSQL database and do not invoke any reset endpoint between the two commands. Then run:

```bash
python scripts/ac19_restart_check.py verify
```

Record the resulting pass/fail output along with the Render restart event/time and the target URL; capture a redacted screenshot or CI log for submission. AC-19 passes only when the ticket, recorded report content, and audit history are unchanged. The script intentionally does not require transient in-memory test-clock state to persist.

## Evidence status as of 2026-11-22

The latest results, including the 17/18 deployed self-run, the 502-based AC-18
failure, the 233/241 external suite, and operator-reported AC-19 pass, are
maintained in [Phase 5 results](phase5-results.md). Do not use the older
green-but-failing workflow reports as passing evidence.

## Submission artifacts

Retain the final design/model mapping, operational runbook, full test reports (including `coverage`), measured performance evidence, recorded restart demonstration, current shared Pod K OpenAPI/spec version, registered URLs, and a concise list of any remaining limitations.
