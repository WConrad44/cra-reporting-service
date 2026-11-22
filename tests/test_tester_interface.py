from fastapi.testclient import TestClient
import httpx

import tester.main as tester_main


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload


def test_tester_setup_run_and_report(monkeypatch):
    def fake_request(method, target_url, path, *, json=None, actor=False):
        if method == "POST" and path == "/test/setup":
            return FakeResponse(201, {"session_id": json["session_id"]})

        if method == "GET" and path.startswith("/test/report?"):
            return FakeResponse(
                200,
                {
                    "coverage": {
                        "code": {
                            "covered": None,
                            "total": None,
                            "basis": "Source lines; instrumentation unavailable",
                        }
                    }
                },
            )

        raise AssertionError(f"unexpected request: {method} {path}")

    monkeypatch.setattr(tester_main, "_request", fake_request)
    monkeypatch.setattr(
        tester_main,
        "_run_suite",
        lambda target: [
            {"test_id": "AC-01", "outcome": "pass", "message": "stubbed success"}
        ],
    )

    client = TestClient(tester_main.app)

    setup = client.post(
        "/test/setup",
        json={"target_url": "https://example.test"},
    )

    assert setup.status_code == 201
    session_id = setup.json()["session_id"]

    before = client.get(
        "/test/report",
        params={"session_id": session_id},
    )
    assert before.status_code == 409

    run = client.post(
        "/test/run",
        json={"session_id": session_id},
    )

    assert run.status_code == 200

    body = run.json()

    assert body["session_id"] == session_id
    assert body["target_url"] == "https://example.test"
    assert body["results"][0]["outcome"] == "pass"
    assert "model" not in body["coverage"]

    report = client.get(
        "/test/report",
        params={"session_id": session_id},
    )

    assert report.status_code == 200
    assert report.json() == body

    rerun = client.post(
        "/test/run",
        json={"session_id": session_id},
    )

    assert rerun.status_code == 409


def test_target_specific_token_is_forwarded(monkeypatch):
    monkeypatch.setenv(
        "TARGET_TOKENS_JSON",
        '{"https://team17.example":"team17-test-token"}',
    )

    headers = tester_main._headers("https://team17.example")

    assert headers["Authorization"] == "Bearer team17-test-token"


def test_phase5_model_coverage_only_for_own_system(monkeypatch):
    monkeypatch.setattr(tester_main, "OWN_SYSTEM_URL", "https://team21.example")
    monkeypatch.setattr(
        tester_main,
        "_run_suite",
        lambda target: [
            {"test_id": "AC-18", "outcome": "pass", "message": "performance passed"}
        ],
    )

    def fake_request(method, target_url, path, *, json=None, actor=False):
        if method == "POST" and path == "/test/setup":
            return FakeResponse(201, {"session_id": json["session_id"]})
        if method == "GET" and path.startswith("/test/report?"):
            return FakeResponse(
                200,
                {
                    "coverage": {
                        "code": {
                            "covered": 50,
                            "total": 100,
                            "basis": "Source-line coverage for app",
                        }
                    }
                },
            )
        raise AssertionError(f"unexpected request: {method} {path}")

    monkeypatch.setattr(tester_main, "_request", fake_request)
    client = TestClient(tester_main.app)

    setup = client.post("/test/setup", json={"target_url": "https://team21.example"})
    assert setup.status_code == 201
    run = client.post("/test/run", json={"session_id": setup.json()["session_id"]})
    assert run.status_code == 200
    coverage = run.json()["coverage"]
    assert coverage["system"] == {
        "covered": 18,
        "total": 19,
        "basis": (
            "The Phase 5 Team 21 tester evaluates AC-01 through AC-18. "
            "AC-19 restart persistence is a recorded owning-team demonstration."
        ),
    }
    assert coverage["model"]["covered"] == 3
    assert coverage["model"]["total"] == 4


def test_tester_errors_use_message_and_source():
    client = TestClient(tester_main.app)
    response = client.post("/test/run", json={"session_id": "unknown"})
    assert response.status_code == 404
    assert response.json() == {
        "message": "Unknown tester session",
        "source": "tester",
    }

    invalid = client.post("/test/run", json={})
    assert invalid.status_code == 400
    assert invalid.json()["source"] == "tester"
