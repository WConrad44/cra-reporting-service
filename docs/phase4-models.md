# Phase 4 system models

These models describe the Team 21 implementation delivered for Phase 4. They replace the
Phase 3-only diagram for the Phase 4 submission.

## Model A — Ticket lifecycle

```mermaid
stateDiagram-v2
    [*] --> received: POST /tickets
    received --> received: PATCH details
    received --> reportable: actively_exploited + aware_at
    received --> closed_nonreportable: not_actively_exploited / invalid
    reportable --> reportable: PATCH details / record reports
    reportable --> closed_resolved: all 3 reports submitted + close

    state "closed (not reportable)" as closed_nonreportable
    state "closed (resolved)" as closed_resolved
```

A human makes the actively-exploited decision. The service automates the consequences:
state transitions, deadlines, report status, draft generation, submission records, and closure.

## Model B — Report status

For a reportable or resolved ticket, status is derived on every read rather than stored.

```text
No submission:
  final report + no corrective/mitigating measure -> awaiting_fix
  now <= due_at                              -> pending
  now > due_at                               -> overdue

Submission recorded:
  submitted_at <= recalculated due_at        -> submitted
  submitted_at > recalculated due_at         -> submitted_late
```

Because status is derived, correcting `aware_at` or `fix.available_at` immediately
re-evaluates whether an existing submission was on time.

## Model C — Draft data

All four drafts contain `ticket_id` and `aware_at`. Reporter identity is never copied
into a draft.

| Field | Early warning | Notification | Final report | User advisory |
|---|---|---|---|---|
| product | required | required | required | required |
| affected versions | required | required | required | required |
| member states | required | required | required | not included |
| vulnerability description | — | required | required | required |
| exploit description | — | required | required | — |
| mitigations taken | — | required | required | — |
| mitigations for users | — | required | required | required |
| sensitivity | — | required | required | — |
| severity + impact | — | — | required | optional |
| malicious actor | — | — | optional | — |
| corrective/mitigating measure | — | — | required | optional |

A successful Article 14 submission stores a content snapshot. Later ticket edits do not
change that locked report.

## Data model

```mermaid
erDiagram
    Ticket ||--o| TicketExtension : extends
    Ticket ||--o{ ReportRecord : has
    Ticket ||--o{ AuditEntry : has

    Ticket {
        string id PK
        string state
        string resolution
        datetime received_at
        datetime aware_at
        text product_json
        text reporter_json
        text member_states_json
        text vulnerability_json
        text fix_json
    }

    TicketExtension {
        string ticket_id PK
        text exploit_json
        text mitigations_json
        text impact
        text malicious_actor
        string sensitivity
    }

    ReportRecord {
        int id PK
        string ticket_id FK
        string report_type
        datetime submitted_at
        string reference
        text content_json
    }

    AuditEntry {
        int id PK
        string ticket_id FK
        int seq
        datetime at
        string actor
        string action
        text changes_json
        text reason
    }
```

The extension table was added so the Phase 4 fields could be persisted without an unsafe
in-place migration of the existing SQLite `tickets` table.

## Architecture / request flow

```mermaid
flowchart LR
    Client[Client / Podmate Tester] --> Render[Render HTTPS]
    Render --> FastAPI[FastAPI routes]
    FastAPI --> Auth[Bearer + X-Actor checks]
    FastAPI --> Validation[Pydantic validation]
    FastAPI --> Domain[Ticket/report domain rules]
    Domain --> Clock[Central test/real clock]
    Domain --> ORM[SQLAlchemy]
    ORM --> DB[(SQLite evaluation database)]
    FastAPI --> Client
```

Phase 4 adds report drafting, submission snapshots, filtering, closure and audit behavior
inside the existing route/domain/database flow. PostgreSQL and durable restart persistence
remain Phase 5 work.
