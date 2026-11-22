"""AC-18 tester profiling without network I/O or reduced coverage."""

import httpx

from tester import main as tester


class Response:
    def __init__(self, status_code=200, ticket_id="t_fake"):
        self.status_code = status_code
        self.ticket_id = ticket_id

    def json(self):
        return {"id": self.ticket_id}


def test_nearest_rank_p95():
    assert tester._nearest_rank_p95(list(range(1, 201))) == 190
    assert tester._nearest_rank_p95(list(range(1, 51))) == 48


def test_ac18_preserves_all_1000_tickets_200_requests_and_four_operations(monkeypatch):
    events = []
    resets = []

    def fake_request(method, target, path, *, json=None, actor=False):
        events.append((method, path, actor))
        if method == "POST" and path == "/tickets":
            return Response(201, ticket_id=f"t_{len(events)}")
        return Response(200)

    monkeypatch.setattr(tester, "_request", fake_request)
    monkeypatch.setattr(tester, "_reset_and_clock", lambda *args: resets.append(args))

    result = tester._run_ac18("https://example.test")
    assert result["test_id"] == "AC-18"
    assert result["outcome"] == "pass", result
    assert len(resets) == 1
    assert len(events) == 1200
    loads = events[:1000]
    measured = events[1000:]
    assert all(method == "POST" and path == "/tickets" for method, path, _ in loads)
    assert len(measured) == 200
    assert sum(method == "GET" and path == "/tickets?state=received" for method, path, _ in measured) == 50
    assert sum(method == "PATCH" for method, _, _ in measured) == 50
    assert sum(method == "GET" and path.endswith("/audit") for method, path, _ in measured) == 50
    assert sum(
        method == "GET" and path.startswith("/tickets/t_") and not path.endswith("/audit")
        for method, path, _ in measured
    ) == 50
    assert "list_received: n=50 p95=" in result["message"]
    assert "get_ticket: n=50 p95=" in result["message"]
    assert "get_audit: n=50 p95=" in result["message"]
    assert "across 200 sequential mixed requests" in result["message"]


def test_ac18_still_fails_on_any_unexpected_measured_status(monkeypatch):
    request_count = 0

    def fake_request(method, target, path, *, json=None, actor=False):
        nonlocal request_count
        request_count += 1
        if method == "POST" and path == "/tickets":
            return Response(201, ticket_id=f"t_{request_count}")
        if request_count == 1014:
            return Response(502)
        return Response(200)

    monkeypatch.setattr(tester, "_request", fake_request)
    monkeypatch.setattr(tester, "_reset_and_clock", lambda *args: None)

    result = tester._run_ac18("https://example.test")
    assert result["outcome"] == "fail"
    assert "502" in result["message"]
    assert request_count == 1200


def test_tester_requests_gzip_and_reuses_http_client(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(tester, "_http", client)
        assert tester._request("GET", "https://example.test", "/health").status_code == 200
        assert tester._request("GET", "https://example.test", "/health").status_code == 200
    assert len(seen) == 2
    assert all(request.headers.get("accept-encoding") == "gzip" for request in seen)
