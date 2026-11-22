from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import AUTH_ONLY


def test_system_test_session_reports_code_coverage():
    client = TestClient(app)
    session_id = "phase5-coverage-session"

    setup = client.post(
        "/test/setup",
        headers=AUTH_ONLY,
        json={"session_id": session_id, "setup": {}},
    )
    assert setup.status_code == 201, setup.text

    # Exercise normal project code after coverage starts.
    health = client.get("/health")
    assert health.status_code == 200

    report = client.get(
        "/test/report",
        headers=AUTH_ONLY,
        params={"session_id": session_id},
    )
    assert report.status_code == 200, report.text
    measure = report.json()["coverage"]["code"]
    assert isinstance(measure["covered"], int)
    assert isinstance(measure["total"], int)
    assert 0 < measure["covered"] <= measure["total"]
    assert "Source-line coverage" in measure["basis"]


def test_system_test_interface_errors_use_message_and_source():
    client = TestClient(app)

    missing = client.get(
        "/test/report",
        headers=AUTH_ONLY,
        params={"session_id": "does-not-exist"},
    )
    assert missing.status_code == 404
    assert missing.json() == {
        "message": "Unknown test session",
        "source": "system",
    }

    invalid = client.post(
        "/test/setup",
        headers=AUTH_ONLY,
        json={},
    )
    assert invalid.status_code == 400
    assert invalid.json()["source"] == "system"
    assert invalid.json()["message"]
