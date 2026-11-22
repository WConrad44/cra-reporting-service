"""Pod K Phase 5 regressions reproduced from Team 17's independent audit."""

import pytest

from conftest import AUTH_ONLY, HEADERS
from test_phase4 import audit, create, full_ticket, set_clock, triage


@pytest.mark.parametrize(
    ("method", "suffix"),
    [("PATCH", ""), ("POST", "/triage")],
)
@pytest.mark.parametrize(
    "ticket_id",
    ["not-an-id", "00000000-0000-0000-0000-000000000000"],
)
def test_unknown_ticket_precedes_malformed_body_and_missing_actor(
    client, method, suffix, ticket_id
):
    valid = create(client)
    before = client.get(f"/tickets/{valid['id']}", headers=AUTH_ONLY).json()
    malformed = client.request(
        method,
        f"/tickets/{ticket_id}{suffix}",
        headers={**AUTH_ONLY, "Content-Type": "application/json"},
        content=b"{bad",
    )
    assert malformed.status_code == 404, malformed.text
    assert malformed.headers["content-type"].startswith("application/problem+json")

    unauthenticated = client.request(
        method,
        f"/tickets/{ticket_id}{suffix}",
        headers={"Content-Type": "application/json"},
        content=b"{bad",
    )
    assert unauthenticated.status_code == 401, unauthenticated.text

    existing = client.request(
        method,
        f"/tickets/{valid['id']}{suffix}",
        headers={**HEADERS, "Content-Type": "application/json"},
        content=b"{bad",
    )
    assert existing.status_code == 400, existing.text
    assert client.get(f"/tickets/{valid['id']}", headers=AUTH_ONLY).json() == before


def test_awareness_change_without_reason_returns_422_and_changes_nothing(client):
    set_clock(client, "2026-10-20T12:00:00Z")
    ticket = create(client, full_ticket())
    triage(client, ticket["id"])
    before = client.get(f"/tickets/{ticket['id']}", headers=AUTH_ONLY).json()
    before_audit = audit(client, ticket["id"])
    changed = client.patch(
        f"/tickets/{ticket['id']}",
        headers=HEADERS,
        json={
            "title": "Must not persist",
            "aware_at": "2026-10-19T11:00:00Z",
        },
    )
    assert changed.status_code == 422, changed.text
    assert changed.json()["errors"][0]["field"] == "change_reason"
    assert client.get(f"/tickets/{ticket['id']}", headers=AUTH_ONLY).json() == before
    assert audit(client, ticket["id"]) == before_audit


def test_recorded_reports_and_advisory_remain_readable_after_resolution(client):
    set_clock(client, "2026-10-20T12:00:00Z")
    ticket = create(client, full_ticket())
    triage(client, ticket["id"])
    for report_type in ("early_warning", "notification", "final_report"):
        response = client.post(
            f"/tickets/{ticket['id']}/reports/{report_type}/submission",
            headers=HEADERS,
            json={},
        )
        assert response.status_code == 200, response.text
    paths = [
        f"/tickets/{ticket['id']}/reports/{report_type}"
        for report_type in ("early_warning", "notification", "final_report", "user_advisory")
    ]
    before = [client.get(path, headers=AUTH_ONLY) for path in paths]
    assert all(response.status_code == 200 for response in before)

    closed = client.post(f"/tickets/{ticket['id']}/close", headers=HEADERS)
    assert closed.status_code == 200, closed.text
    assert closed.json()["resolution"] == "resolved"
    after = [client.get(path, headers=AUTH_ONLY) for path in paths]
    assert all(response.status_code == 200 for response in after)
    assert [response.json() for response in after] == [response.json() for response in before]


def test_large_ticket_listing_uses_gzip_when_requested(client):
    for number in range(20):
        created = client.post(
            "/tickets",
            headers=HEADERS,
            json={
                "source": "customer",
                "title": f"Compression test {number}",
                "description": "Repeated example description for larger responses.",
                "product": {"manufacturer": "Acme", "name": "Router"},
            },
        )
        assert created.status_code == 201, created.text

    listing = client.get(
        "/tickets",
        headers={**AUTH_ONLY, "Accept-Encoding": "gzip"},
    )
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 20
    assert listing.headers.get("content-encoding") == "gzip"
    assert "Accept-Encoding" in listing.headers.get("vary", "")
