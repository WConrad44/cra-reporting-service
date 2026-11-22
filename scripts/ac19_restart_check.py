from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


STATE_FILE = Path(os.getenv("AC19_STATE_FILE", "ac19-state.json"))
BASE_URL = os.getenv(
    "CRA_BASE_URL",
    "https://team21-cra-reporting-service.onrender.com",
).rstrip("/")
TOKEN = os.getenv("CRA_API_TOKEN", "")
AUTH = {"Authorization": f"Bearer {TOKEN}"}
ACTOR = {**AUTH, "X-Actor": "team21-ac19"}


def request(method: str, path: str, **kwargs) -> httpx.Response:
    response = httpx.request(
        method,
        BASE_URL + path,
        headers=kwargs.pop("headers", AUTH),
        timeout=60,
        follow_redirects=True,
        **kwargs,
    )
    response.raise_for_status()
    return response


def persisted_view(ticket: dict, report: dict, audit: list[dict]) -> dict:
    return {
        "ticket": {
            key: ticket.get(key)
            for key in (
                "id",
                "source",
                "title",
                "description",
                "product",
                "member_states",
                "state",
                "resolution",
                "received_at",
                "aware_at",
            )
        },
        "report": {
            key: report.get(key)
            for key in (
                "ticket_id",
                "type",
                "submitted_at",
                "reference",
                "content",
            )
        },
        "audit": audit,
    }


def prepare() -> None:
    if not TOKEN:
        raise SystemExit("Set CRA_API_TOKEN before running this script.")

    request("POST", "/test/reset")
    request(
        "PUT",
        "/test/clock",
        json={"now": "2026-11-22T18:00:00Z"},
    )

    created = request(
        "POST",
        "/tickets",
        headers=ACTOR,
        json={
            "source": "external_researcher",
            "title": "AC-19 restart persistence",
            "description": "Phase 5 persistence demonstration.",
            "product": {
                "manufacturer": "Team 21",
                "name": "CRA Service",
                "affected_versions": ["0.5.0"],
            },
            "member_states": ["DE"],
        },
    ).json()
    ticket_id = created["id"]

    request(
        "POST",
        f"/tickets/{ticket_id}/triage",
        headers=ACTOR,
        json={
            "decision": "actively_exploited",
            "aware_at": "2026-11-22T17:00:00Z",
            "reason": "AC-19 persistence demonstration.",
        },
    )
    request(
        "POST",
        f"/tickets/{ticket_id}/reports/early_warning/submission",
        headers=ACTOR,
        json={"reference": "AC19-EW"},
    )

    ticket = request("GET", f"/tickets/{ticket_id}").json()
    report = request("GET", f"/tickets/{ticket_id}/reports/early_warning").json()
    audit = request("GET", f"/tickets/{ticket_id}/audit").json()

    STATE_FILE.write_text(
        json.dumps(persisted_view(ticket, report, audit), indent=2),
        encoding="utf-8",
    )
    print(f"Prepared AC-19 state for ticket {ticket_id}.")
    print("Restart/redeploy the Render system service now, then run: python scripts/ac19_restart_check.py verify")


def verify() -> None:
    if not TOKEN:
        raise SystemExit("Set CRA_API_TOKEN before running this script.")
    if not STATE_FILE.exists():
        raise SystemExit(f"{STATE_FILE} is missing; run prepare first.")

    expected = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    ticket_id = expected["ticket"]["id"]

    ticket = request("GET", f"/tickets/{ticket_id}").json()
    report = request("GET", f"/tickets/{ticket_id}/reports/early_warning").json()
    audit = request("GET", f"/tickets/{ticket_id}/audit").json()
    actual = persisted_view(ticket, report, audit)

    if actual != expected:
        print("AC-19 FAILED: persisted state changed across restart.")
        print(json.dumps({"expected": expected, "actual": actual}, indent=2))
        raise SystemExit(1)

    print("AC-19 PASSED: ticket, recorded report, and audit history survived the service restart unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "verify"])
    args = parser.parse_args()
    {"prepare": prepare, "verify": verify}[args.action]()
