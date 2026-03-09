from fastapi.testclient import TestClient

from ppapcheck.main import app


client = TestClient(app)


def test_sample_report_endpoint_returns_blocked_result():
    response = client.get("/api/samples/hybrid_blocked")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_decision"] == "BLOCK_SUBMISSION"
    assert body["submission_mode"] == "HYBRID"


def test_dashboard_renders():
    response = client.get("/")

    assert response.status_code == 200
    assert "Submission Readiness Review" in response.text
    assert "Machine-Readable Output" in response.text

