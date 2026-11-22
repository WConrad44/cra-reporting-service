# Phase 5 design requirements

These design requirements describe the Team 21 Phase 5 increment and provide the mapping
required for Phase 5 model coverage.

| ID | Design requirement | Evidence |
|---|---|---|
| DR-01 | The deployed application persists tickets, report snapshots, and audit entries through SQLAlchemy using an external PostgreSQL database when `DATABASE_URL` is PostgreSQL. | PostgreSQL CI job plus AC-19 restart demonstration |
| DR-02 | The course test-session interface measures source-line coverage from system setup until system report retrieval without counting the report request itself. | `tests/test_phase5.py::test_system_test_session_reports_code_coverage` |
| DR-03 | The Team 21 tester reports system coverage through AC-18 and includes Phase 5 model coverage only when targeting Team 21's own system. | `tests/test_tester_interface.py` and AC-18 |
| DR-04 | The deployed service satisfies the Pod K performance target at 1,000 stored tickets: p95 of 200 sequential mixed requests is at most one second. | AC-18 performance result |

Model coverage in the tester is therefore based on DR-01 through DR-04. The automated
tester evaluates DR-02, DR-03, and DR-04. DR-01 requires the owning team's recorded
restart demonstration (AC-19), so it is intentionally not counted as covered by a normal
tester run.
