# Team 21 JSON-file intake channel

The common Pod K API is the shared interface. This optional Team 21 CLI is a separate
operator/researcher intake path for a JSON vulnerability report. It uses the same
`POST /tickets` endpoint, authorization, audit actor, and validation rules as the
official API. It does not submit reports to ENISA or CSIRT, ingest email automatically,
or replace the shared HTTP interface.

## Use on macOS / Linux

With the Team 21 repository checked out:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

export CRA_BASE_URL=https://team21-cra-reporting-service.onrender.com
export CRA_ACTOR=team21-research-intake
read -s CRA_API_TOKEN
export CRA_API_TOKEN

python scripts/intake_ticket.py examples/intake-ticket.json
```

The input is a JSON object matching the Pod K `POST /tickets` contract. Use
`examples/intake-ticket.json` as a non-sensitive example; it contains fictitious
reporter details. **Do not commit real reporter information or a bearer token**.

Successful output contains only `id`, `state`, and `received_at` (no reporter).
The ticket is stored by the normal SQLAlchemy/PostgreSQL application and audited using
`CRA_ACTOR`. The script exits nonzero for invalid input, network failures, or HTTP errors.

This CLI is an intentionally narrow file-to-API intake channel. Human handling of
submission triage and subsequent Article 14 reporting remains required.

## Validation

```bash
python -m pytest -q tests/test_intake_ticket.py
```

This tests the HTTP request contract with a mock transport; live end-to-end intake
requires running the CLI on the evaluation deployment. Any live test creates a ticket
and must be coordinated with other evaluation tests.
