"""Tests for the optional Phase 5 JSON-file intake channel."""

import httpx
import pytest

from scripts.intake_ticket import submit_intake


def test_intake_posts_ticket_to_registered_api_without_disclosing_reporter():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["actor"] = request.headers["X-Actor"]
        seen["authorization"] = request.headers["Authorization"]
        seen["body"] = request.content
        return httpx.Response(
            201,
            json={
                "id": "t_intake_test",
                "state": "received",
                "received_at": "2026-11-22T00:00:00Z",
                "reporter": {"contact": "private@example.invalid"},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = submit_intake(
            {"source": "external_researcher", "title": "Example"},
            base_url="https://system.example.test/",
            api_token="test-token",
            actor="researcher-intake",
            client=client,
        )
    assert result == {
        "id": "t_intake_test",
        "state": "received",
        "received_at": "2026-11-22T00:00:00Z",
    }
    assert seen["path"] == "/tickets"
    assert seen["actor"] == "researcher-intake"
    assert seen["authorization"] == "Bearer test-token"
    assert b"external_researcher" in seen["body"]


def test_intake_rejects_missing_token_and_invalid_shape_without_network():
    with httpx.Client(transport=httpx.MockTransport(lambda request: pytest.fail("network used"))) as client:
        with pytest.raises(ValueError, match="CRA_API_TOKEN"):
            submit_intake({}, base_url="https://example.test", api_token="", actor="tester", client=client)
        with pytest.raises(ValueError, match="JSON object"):
            submit_intake([], base_url="https://example.test", api_token="test", actor="tester", client=client)


def test_intake_failure_does_not_echo_reporter_or_payload():
    private_marker = "reporter-private-marker"

    def handler(request):
        return httpx.Response(400, json={"message": private_marker})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError) as exc:
            submit_intake(
                {"reporter": {"contact": private_marker}},
                base_url="https://example.test",
                api_token="test",
                actor="tester",
                client=client,
            )
    assert private_marker not in str(exc.value)
    assert "HTTP 400" in str(exc.value)
