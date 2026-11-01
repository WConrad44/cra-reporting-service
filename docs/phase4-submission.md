# Phase 4 submission draft — Team 21

> Finalize the two bracketed deployment/cross-team result fields after the automated
> deployed runs finish. All other text reflects the delivered implementation.

## Q1 Delivered Increment

### Q1.1 Increment description

Phase 4 extends the deployed vulnerability-ticket service from intake and triage into the
full CRA reporting workflow. Security or compliance staff can now update investigation data,
view live obligation status, generate all four drafts, record the three Article 14 submissions,
close a completed ticket, filter work by state/status, and inspect an append-only audit history.
The reporting workflow supports the Article 14(2) early-warning, vulnerability-notification,
and final-report obligations while retaining the Article 13(17) vulnerability-intake foundation.
The actively-exploited decision remains a human responsibility; the software automates the
workflow and consequences after that decision. Reporter identity remains limited to the
single-ticket response as required by REQ-15.

- REQ-05 — Report status | Status: complete | Demonstrated by: AC-06
- REQ-06 — Updates/recalculation | Status: complete | Demonstrated by: AC-07
- REQ-07 — Report drafts | Status: complete | Demonstrated by: AC-08
- REQ-08 — Submission recording | Status: complete | Demonstrated by: AC-09
- REQ-09 — Closure | Status: complete | Demonstrated by: AC-10
- REQ-10 — Listing/filtering | Status: complete | Demonstrated by: AC-11
- REQ-11 — Audit log | Status: complete | Demonstrated by: AC-12
- REQ-12 — Robust error behavior | Status: complete | Demonstrated by: AC-13
- REQ-15 — Reporter confidentiality | Status: complete | Demonstrated by: AC-16

### Q1.2 Comparison with the Phase 2 plan

The Phase 3 milestone from Phase 2 Section 6.1 remains intact: deployment, authentication,
test controls, intake, triage, and deadline calculation continue to pass regression tests.
Phase 4 then delivered the full reporting workflow planned in Phase 2 Section 6.2
(REQ-05 through REQ-11 and REQ-15), with no shared capability removed. Cross-team
clarifications changed a few edge-case interpretations but did not reduce scope. PostgreSQL
was not adopted yet; SQLite remains the evaluation database because durable restart
persistence is still scheduled for Phase 5 under REQ-18.

## Q2 Deployment and Operation

### Q2.1 Deployed web service

The system is deployed on Render in the Virginia region as a Python/FastAPI HTTPS service at
`https://cra-phase3.onrender.com`; the automated tester is separately deployed at
`https://cra-phase3-tester.onrender.com`. Both services deploy from the `main` branch of
`WConrad44/cra-reporting-service`; the Phase 4 application is version 0.4.0 and the optimized
tester is version 0.4.2. The Phase 4 system implementation landed at
`6230ee3479a15b8aae296bed6c42ee260334ff4e`, and the final tester parser/runtime changes
landed at `de341c0803ebe1030cb53c857e8085382daf7046`; later evidence-only commits do not
change the service behavior. GitHub Actions validates every main update before it is treated
as release evidence. These are free
Render services and are not guaranteed to remain warm while idle, so test runs first use the
health/OpenAPI endpoints to wake and verify the deployment.

### Q2.2 Registry and team documentation

Registry entry: ECE 30861 class deployed-service registry, Team 21 system/tester row |
Updated on: **[confirm registry update date]**

Team documentation:
`https://github.com/WConrad44/cra-reporting-service` (README and
`docs/phase4-models.md`) | Updated on: October 31, 2026.

### Q2.3 Operational experience supported by observability evidence

The Phase 4 evaluation service stores tickets, report snapshots, extension fields, and audit
entries through SQLAlchemy in SQLite; `POST /test/reset` deletes all four data groups and
releases test state as defined by the test controls. Bearer credentials and target-specific tester
tokens are stored as Render environment variables rather than committed to GitHub. Render
request/deployment logs are used for HTTP failures and startup problems, while GitHub Actions
records dependency checks, compilation, Ruff correctness checks, and pytest results. A deployed
validation workflow queried both Render OpenAPI endpoints and observed
`system: 0.4.0` and `tester: 0.4.1`, demonstrating that deployment/version signals are
available before tests execute.

## Q3 Implementation and Interface Conformance

### Q3.1 Operation status

- GET /health | Requirement(s): deployment/availability | Implemented: yes |
  Success responses conform: yes | Error responses conform: n/a.
  Integration: lightweight FastAPI route; no database/auth dependency.

- POST /tickets | REQ-01, REQ-12, REQ-13, REQ-14 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: Pydantic validation -> ticket service -> Ticket/TicketExtension + created audit entry.

- GET /tickets | REQ-10, REQ-15 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: SQLAlchemy read -> live obligation serialization -> filters/order -> reporter removal.

- GET /tickets/{id} | REQ-04, REQ-05, REQ-15 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: ticket/report records are combined into live status; this is the only read that exposes reporter data.

- PATCH /tickets/{id} | REQ-04, REQ-06, REQ-11, REQ-12 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: TicketUpdate validation -> one-level merge -> time-rule checks -> immediate deadline/status recalculation -> audit entry only when data changes.

- POST /tickets/{id}/triage | REQ-02, REQ-03, REQ-04, REQ-11 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: human decision is validated, state/awareness is updated, and a triage audit entry is committed atomically.

- GET /tickets/{id}/reports/{type} | REQ-07, REQ-15 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: Model C selects content/missing fields; submitted reports read their locked snapshot.

- POST /tickets/{id}/reports/{type}/submission | REQ-05, REQ-08, REQ-11 |
  Implemented: yes | Success responses conform: yes | Error responses conform: yes.
  Integration: report order, required fields and submission time are checked before a ReportRecord snapshot and audit entry are committed.

- POST /tickets/{id}/close | REQ-09, REQ-11 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: closure requires all three Article 14 ReportRecords, then records resolved/closed plus audit.

- GET /tickets/{id}/audit | REQ-11, REQ-15 | Implemented: yes |
  Success responses conform: yes | Error responses conform: yes.
  Integration: append-only AuditEntry rows are returned by sequence and reporter changes are represented as redacted.

- POST /test/reset | REQ-16 | Implemented: yes | Success/error responses conform: yes.
  Integration: clears audit, report, extension and ticket data in dependency order.

- GET/PUT/DELETE /test/clock | REQ-13, REQ-16 | Implemented: yes |
  Success/error responses conform: yes.
  Integration: all domain time calculations use one centralized real/fixed UTC clock.

The separate course-wide `POST /test/setup` and `GET /test/report` endpoints are also
implemented; the course setup endpoint intentionally does not require the Pod K `X-Actor`
header.

### Q3.2 Contract changes and pod communication

Contract version at delivery: shared `openapi.yaml` is still labeled `0.1.0-draft` on
`pod-k-shared/main`; Team 21's runtime also implements the Phase 4 clarifications agreed by
email with Team 17. Those clarifications cover ignored awareness times on non-reportable
triage, deterministic listing tie-breaks, 409 for drafts on never-reportable tickets, dynamic
`submitted_late` recalculation, no audit entry for a no-op edit, 422 for future
`fix.available_at`, corrective/mitigating-measure wording, an explicit `unknown` value,
and removal of X-Actor from the course-wide test setup endpoint. Pod agreement:
Teams 17 and 21 email thread in late October 2026. Intentional deviation/resolution plan:
there is no intended runtime divergence, but Team 17 still needs to merge the corresponding
shared-contract version update so `pod-k-shared/main` matches the agreed behavior.

## Q4 Automated Validation

### Q4.1 Test runner and execution

Base URL override: Team 21's deployed tester accepts an arbitrary target URL in
`POST /test/setup` as `{"target_url":"https://..."}`; no test code is edited.

Response received: deployed OpenAPI checks returned Team 21 system version `0.4.0` and
tester version `0.4.1`; `GET /health` returns HTTP 200 with `{"status":"ok"}`.

Conforms to spec: yes for the delivered Team 21 implementation and the agreed Phase 4
clarifications.

Known deviations: the shared repository's OpenAPI document has not yet been version-updated
to contain all of the already-agreed Phase 4 clarifications.

### Q4.2 Tests for new functionality

- AC-06 | REQ-05 | `test_ac06_statuses_and_submitted_late_recalculate` |
  Type: boundary/success | Automated: yes.
- AC-07 | REQ-06 | `test_ac07_updates_recalculate_and_reject_invalid_times` |
  Type: success/failure/boundary | Automated: yes.
- AC-08 | REQ-07, REQ-15 | `test_ac08_model_c_drafts_and_privacy` |
  Type: success/missing-field | Automated: yes.
- AC-09 | REQ-05, REQ-08 | `test_ac09_submission_order_missing_fields_and_locked_snapshot` |
  Type: success/failure | Automated: yes.
- AC-10 | REQ-09 | `test_ac10_complete_lifecycle_and_close` |
  Type: success/state conflict | Automated: yes.
- AC-11 | REQ-10, REQ-15 | `test_ac11_list_filters_and_tie_breaks` |
  Type: success/ordering | Automated: yes.
- AC-12 | REQ-11 | `test_ac12_audit_is_append_only_and_failures_add_nothing` plus
  `test_ac12_reporter_only_update_is_audited_without_leaking_contact` |
  Type: success/failure/privacy | Automated: yes.
- AC-13 | REQ-12 | `test_ac13_many_malformed_requests_never_5xx_or_change_data` |
  Type: robustness/failure | Automated: yes; 500 malformed requests.
- AC-16 | REQ-15 | `test_ac16_reporter_confidentiality_across_reads_and_errors` |
  Type: privacy | Automated: yes.

Oracles: expected values come from the agreed Phase 2 requirement text, Models B/C/D, and
the common interface contract rather than from either implementation. Model D E1-E8 was
independently checked by Team 21 against the Phase 2 formulas, then reproduced exactly by
the deployed Team 21 service (8/8), giving a separate check on the time/deadline oracle.

### Q4.3 Regression and static checks

The original Phase 3 regression tests remain in the suite alongside the new Phase 4 tests,
so changes to reporting behavior are checked without dropping intake, triage, authentication,
clock, timestamp, and course-interface coverage. GitHub Actions runs dependency validation,
Python compilation, Ruff correctness checks, and pytest on every push/PR to main; defects
found during independent testing (X-Actor setup, token forwarding, fix updates, reporter-audit
privacy) were converted into regression tests before merge. The finalized Phase 4 main CI run
reported **26 passed, 0 failed**.

CI run: `https://github.com/WConrad44/cra-reporting-service/actions/runs/41262343264`
(the later main revisions run the same checks).

### Q4.4 Static checks

CI runs `pip check`, `python -m compileall app tester tests`, and Ruff correctness rules
(`E9,F63,F7,F82`) before pytest. A failure makes the Actions job fail and was used as a merge
gate for the Phase 4 pull requests; the check was intentionally limited to correctness rules
rather than retroactively making Phase 4 a full style-refactoring task.

CI run: `https://github.com/WConrad44/cra-reporting-service/actions/runs/41262343264`.

### Q4.5 Test results against the deployed system

Run date/time: October 31, 2026 | Version tested: **Team 21 system 0.4.0 / tester 0.4.2; main revision de341c0803ebe1030cb53c857e8085382daf7046**

Tests run: **17** | Passed: **17** | Failed: **0** | Skipped: **0**

Failure: **none**. Evidence: GitHub Actions deployed self-validation run `41263026888`.

## Q5 Updated System Models

### Q5.1 Model updates

- Ticket lifecycle/state model | Changed: yes | Phase 4 adds report recording and resolved
  closure while retaining human triage | Location: `docs/phase4-models.md`.
- Report-status model | Changed: yes | Implements live pending/overdue/submitted/
  submitted_late behavior and recalculation after time corrections |
  Location: `docs/phase4-models.md`.
- Model C draft-information model | Changed: no fundamental Phase 2 field mapping; now
  implemented in code with locked submitted snapshots and the agreed unknown-value behavior |
  Location: `docs/phase4-models.md`.
- Architecture/data-flow model | Changed: yes | Actual implementation uses FastAPI,
  Pydantic, SQLAlchemy, SQLite, TicketExtension, ReportRecord and AuditEntry tables rather
  than the originally planned PostgreSQL design | Location: `docs/phase4-models.md`.

### Q5.2 Model-implementation consistency

We compared the route/service/database code with the common contract and exercised each
modeled transition through automated tests. One concrete divergence from the Phase 2 design
was persistence: Phase 2 proposed PostgreSQL, while the delivered Phase 4 evaluation build
still uses SQLite with separate TicketExtension, ReportRecord and AuditEntry tables, so the
architecture model was corrected to show the actual components. Model D also exposed a
Phase 3 implementation gap where `PATCH` initially rejected `fix.available_at`; the code
was corrected and the shared E1-E8 runner then passed 8/8. The current models therefore
describe the delivered code rather than the originally proposed architecture.

## Q6 Pod Cross-Team Readiness

### Q6.1 Cross-team test

Our tests -> Team 17 service | Date: October 31, 2026 |
Run/passed: **17/11 in the last complete report**. That report listed failures in AC-02,
AC-06, AC-08, AC-09, AC-10 and AC-11. AC-02 was subsequently identified as a Team 21
tester defect (it ignored `application/problem+json`) and was fixed; the five remaining
observable mismatches are AC-06, AC-08, AC-09, AC-10 and AC-11. A corrected final rerun
reached the Render tester but hit a 502 long-request gateway before a new report was returned,
so the completed 11/17 report remains the recorded directional count. Main problem/owner:
**Team 17/shared-contract alignment for the five remaining behavior mismatches; Team 21 owns
the already-fixed tester runtime/parser issues.** Evidence: cross-team runs `41262667904`
and `41263167229`.

Team 17 tests -> our service | Date: October 31, 2026 |
Run/passed: **0/0; setup returned HTTP 401 before the suite executed** |
Main problem and owner: **cross-team tester authentication/configuration. The published
shared repo does not expose enough of Team 17's hosted tester wrapper to determine whether
the 401 is its own access control or failure to forward Team 21's target token, so Team 17
needs to verify its deployed tester configuration/access instructions.**

Coverage: Team 21's Phase 4 tester covers AC-01 through AC-17 except the Phase 5
performance/restart work; AC-18/AC-19 remain Phase 5. Code-coverage counts are reported as
unavailable on the deployed target because source instrumentation is not enabled.

### Q6.2 Specification issues discovered

Issue: the shared triage schema made `aware_at` optional except for
`actively_exploited`, but did not say what should happen if an awareness time was supplied
with `not_actively_exploited` or `invalid`. Team 21 originally rejected that request while
Team 17 proposed accepting it and ignoring the irrelevant time, so two valid-looking
implementations could disagree. The pod agreed by email to accept the request, ignore
`aware_at`, close the ticket, and apply no Article 14 deadlines; Team 21 now implements and
tests that decision. The same coordination thread resolved the future-fix, unknown-value,
tie-break, no-op-audit, submission-status, and course X-Actor edge cases; the remaining
process task is to merge those clarifications into the shared OpenAPI version.

## Q7 Status, Limitations and Next Phase Adjustments

### Q7.1 What changed and what remains incomplete

Changed since Phase 2:
- REQ-05/06: live obligation status and full updates/deadline recalculation are implemented.
- REQ-07/08/09: four drafts, locked Article 14 submission records, and completed-ticket closure are implemented.
- REQ-10/11/15: deterministic listing/filtering, append-only audit history, and reporter confidentiality are implemented.
- REQ-12: AC-13 now sends 500 malformed requests and verifies no 5xx/state corruption.
- Cross-team integration: target-specific token forwarding, course `/test/setup` header behavior, Model D fix updates, and the late-October pod clarifications are incorporated.

Remaining incomplete:
- REQ-17 / AC-18: 1,000-ticket/95%-under-one-second performance validation is Phase 5.
- REQ-18 / AC-19: durable persistence across a service restart is Phase 5; SQLite on Render is not claimed as durable restart storage.
- Phase 5 operations: migrate/finalize durable database hosting, run restart evidence, and stabilize the final contract/test suite.
- Shared artifact: Team 17 still needs to merge the updated OpenAPI wording/version reflecting the already-agreed Phase 4 clarifications.

### Q7.2 Known limitations and defects

- LIM-01 | SQLite/Render restart persistence is not guaranteed | Affects: REQ-18 |
  Severity: high | Workaround: do not rely on evaluation data across service restarts |
  Target phase: 5.
- LIM-02 | REQ-17 performance at 1,000 tickets has not yet been measured |
  Affects: REQ-17 | Severity: medium | Workaround: warm the free Render service before functional testing |
  Target phase: 5.
- LIM-03 | Free Render services can cold-start after idle periods |
  Affects: test/runtime latency | Severity: low | Workaround: call `/health`/OpenAPI before a timed suite |
  Target phase: 5 operational hardening.
- LIM-04 | Shared `openapi.yaml` on the pod repository still trails the Phase 4 email decisions |
  Affects: cross-team contract interpretation | Severity: medium | Workaround: use the written pod decisions and regression tests until the shared PR merges |
  Target phase: immediate/Phase 4 closeout.

### Q7.3 Adjustments to the next phase milestone

The Phase 5 milestone from Phase 2 still holds: performance, restart persistence, final
intake/operations work, and stabilization remain the correct next capabilities. Phase 4
substantially reduced the earlier risk that the two teams would interpret deadline and report
workflow behavior differently, because the ambiguous edge cases were surfaced and resolved
through independent tests and email coordination. The major remaining technical risk is
REQ-18 persistence, followed by REQ-17 performance on free hosting; PostgreSQL/durable
storage and the controlled restart demonstration should therefore be prioritized before
performance tuning. A new coordination risk is contract drift between agreed email behavior
and `pod-k-shared/main`, so the OpenAPI update should be merged before the final cross-team
freeze; that shared artifact change requires pod agreement but no reduction in project scope.
