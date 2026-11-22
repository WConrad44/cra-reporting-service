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

The reported Team 17 241-case run overlapped with Team 21's earlier deployed
self-validation, which also resets the database. Therefore the three 404s for
resolved-draft reads are not conclusive until a non-overlapping rerun. We added
a local regression that verifies all recorded report drafts and the advisory
remain readable after closure, without changing the existing correct behavior.

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
