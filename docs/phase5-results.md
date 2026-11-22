# Phase 5 acceptance evidence and outstanding verification

Status recorded on November 22, 2026. This is an evidence ledger, not a declaration
that all tests have passed. Keep the deployed commit SHA, dates and artifacts together
when updating it.

## Team 21 deployed system and tester

| Role | URL |
|---|---|
| System | https://team21-cra-reporting-service.onrender.com |
| Tester | https://cra-phase3-tester.onrender.com |

System service uses FastAPI, SQLAlchemy and a Render PostgreSQL database via its
`DATABASE_URL`. Verify the database binding in Render privately; CI PostgreSQL
success by itself does not establish Render's durable storage behavior.

## Verified and reported evidence

| Item | Evidence | Interpretation |
|---|---|---|
| Local/CI regression | [GitHub CI 45060015348](https://github.com/WConrad44/cra-reporting-service/actions/runs/45060015348), merged commit `87f76d7` | Both SQLite and PostgreSQL jobs succeeded; 38 tests in each |
| Deployed self suite | [GitHub run 45060015396](https://github.com/WConrad44/cra-reporting-service/actions/runs/45060015396) | **17 pass, 1 fail**, not a complete Phase 5 pass |
| AC-18 performance | Same deployed self report | Loaded 1,000 tickets; reported p95=0.076 seconds over 200 sequential requests, but HTTP 502 responses began at index 13; **FAIL despite fast p95** |
| Reciprocal cross-team workflow | [GitHub run 45060015308](https://github.com/WConrad44/cra-reporting-service/actions/runs/45060015308) | Team 21 → Team 17 HTTP 502; reverse setup blocked by missing `TEAM17_TESTER_TOKEN` GitHub secret |
| Team 17 independent suite against Team 21 | [Team 17 Phase 5 SYSTEM.md](https://github.com/team17-ece30861/pod-k-shared/blob/main/team17/SYSTEM.md) | 233/241; four error-precedence mismatches, one missing-awareness-reason mismatch, three missing resolved-draft reads |
| AC-19 restart script | Team 21 operator's terminal output, November 22 | `prepare` created ticket `t_b7b2f068ab17`; `verify` printed `AC-19 PASSED`: ticket, recorded report and audit data compared equal. A Render restart-event screenshot is still needed to independently show a restart actually occurred between commands |

The Team 17 241-case run's three resolved-draft 404s are not yet explained.
We have not established whether a concurrent database reset occurred. The
current route appears to support reading resolved drafts, and a local regression
now verifies that all recorded reports and the user advisory remain readable
after closure. A fresh, coordinated, non-overlapping independent run is needed
to verify the deployed behavior.

## November 22 live Phase 5 verification

- [Independent Team 17 functional run 45063917221](https://github.com/WConrad44/cra-reporting-service/actions/runs/45063917221):
  **241/241 passed** against Team 21, 0 failures.
- [Independent generated malformed run 45064603073](https://github.com/WConrad44/cra-reporting-service/actions/runs/45064603073):
  **664/664 distinct malformed inputs** over 133 fault categories; 0 HTTP 5xx,
  0 contract mismatches.
- [Independent performance run 45065040575, attempt 2](https://github.com/WConrad44/cra-reporting-service/actions/runs/45065040575):
  **AC-18 PASS**, 1,000 tickets; 200 validated sequential requests;
  p50 95.2 ms, p95 **583.0 ms**, p99 756.8 ms; 0 unexpected responses.
  The earlier attempt at the same run ID failed at p95 1710.7 ms.
- [Team 21 deployed tester run 45067009901](https://github.com/WConrad44/cra-reporting-service/actions/runs/45067009901):
  **17/18 passed**; AC-18 p95 **3778 ms**, 200 requests, 0 unexpected statuses.

**These AC-18 samples are not directly comparable.** The Team 21 benchmark
loads 1,000 all-received tickets and executes 50 large
`GET /tickets?state=received` operations, plus 50 each of single-ticket GET,
PATCH, and audit GET. The independent Team 17 benchmark has a different
dataset and request mix, including 20 total list requests. In addition,
Team 21's deployed tester runs on Render, whereas the Team 17 tester runs on
a GitHub-hosted runner. Neither run establishes how much of the difference is
caused by system JSON encoding, dataset, or tester CPU.

The **tester efficiency and list serialization PR** directly addresses these
differences without weakening AC-18: the same 1,000/200 and 50/50/50/50
Team 21 mix is retained; results now report per-operation p95. The
`Deployed self-validation` workflow can run the same tester source on a
GitHub runner (default) or the published Render tester (optional), with
execution host labelled in its evidence. Both modes target the same deployed
Team 21 service; the GitHub mode does **not** count as proof that the
published Render tester itself is fast. A live rerun is required.

## Post-merge regression verification

[GitHub CI run 45063121354](https://github.com/WConrad44/cra-reporting-service/actions/runs/45063121354)
passed on the merged commit `528887be9f2ff3629cea5f0aabf1f5c0fcaa0b64`
(November 22, 2026). Both the SQLite and PostgreSQL jobs passed all
48 regression tests. This does **not** certify the deployed AC-18 or
reciprocal cross-team acceptance runs.

The final shared Pod K [OpenAPI contract](https://github.com/team17-ece30861/pod-k-shared/blob/main/openapi.yaml)
is version **0.3.0**, verified against the file's `info.version`.

## New work awaiting post-merge deployed verification

- Contract: return 404 for an unknown PATCH/triage target even when the JSON
  body is malformed (after checking authorization); return 422 for an awareness
  time change missing its reason.
- Regression tests: unknown target error priority; awareness failure
  atomicity; resolved drafts; compression of large ticket lists.
- Performance optimization: low-compression-level HTTP gzip for large responses.
  This lowers response traffic but must not be claimed to fix Render HTTP 502
  failures until AC-18 reruns pass on the deployed service.
- Separate Team 21 JSON-file CLI intake channel:
  [instructions](phase5-intake.md). Its unit tests use mock HTTP; capture a
  redacted live run as evidence if the intake-channel feature is graded.
- Manual GitHub workflow for the *independent* Team 17 functional, malformed,
  and AC-18 performance tools.

## Sequence to complete acceptance

1. Review and merge the contract/performance/intake pull request after CI
   passes. Let both Team 21 Render services deploy the new commit.
2. In GitHub Actions repository secrets, configure `TEAM17_TESTER_TOKEN`
   for the protected Team 17 tester and `TEAM21_API_TOKEN` for independent
   evidence. Never commit token values or put them in workflow dispatch inputs.
3. Coordinate with Team 17 and staff so **only one destructive suite** runs
   against each evaluation deployment. All reset-using workflows in Team 21
   are manual-only; share concurrency group `pod-k-deployed-validation`.
4. Run **Deployed self-validation** on Team 21: expect all AC-01 through
   AC-18 to pass. Save its report artifact, specifically AC-18's response
   statuses and verified p95 ≤ 1 second.
5. Run **Independent Phase 5 acceptance evidence (Team 17 runner)** in
   GitHub Actions. Select `performance`, `malformed`, and
   `full-functional` in separate non-overlapping runs. Download the
   uploaded JSON/Markdown evidence; only passing runs qualify.
6. With Team 17's agreement, run the **Cross-team validation** workflow in
   both directions. Record each reported pass/fail result and coverage
   measures. Any 502/timeout/401 is a failure or configuration gap, not a pass.
7. Complete the AC-19 evidence with a redacted screenshot showing the
   Render web-service restart time between the two existing script outputs.
   Do not reset the database between `prepare` and `verify`.
8. Record the deployed commit SHA, date, spec/OpenAPI contract version
   (Pod K contract 0.3.0), remaining known limitations, operations guide
   and completed results in the final assignment.

If the canonical system still restarts under AC-18, collect Render resource /
instance logs and test on a compute tier with sufficient headroom. The p95
cannot be claimed as a pass if HTTP requests return 502. A paid tier is an
operational choice, not an automatic software fix.
