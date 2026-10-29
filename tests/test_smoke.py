from fastapi.testclient import TestClient

from app.main import app


def test_complete_workflow():
    with TestClient(app) as client:
        learner = client.post("/api/learners", json={"name": "Smoke Learner", "language": "python", "skill_level": "beginner"}).json()
        session = client.post(f"/api/learners/{learner['id']}/sessions").json()
        result = client.post(
            "/api/submissions",
            json={
                "session_id": session["session_id"],
                "code": "def sum_values(values):\n    return sum(values)",
                "idempotency_key": "smoke-1",
            },
        )
        assert result.status_code == 200
        assert result.json()["result"]["passed"] is True
        audit = client.get(f"/api/learners/{learner['id']}/audit").json()
        assert any(event["type"] == "submission_evaluated" for event in audit)


def test_retry_is_idempotent():
    with TestClient(app) as client:
        learner = client.post("/api/learners", json={"name": "Retry Learner", "language": "python", "skill_level": "beginner"}).json()
        session = client.post(f"/api/learners/{learner['id']}/sessions").json()
        payload = {"session_id": session["session_id"], "code": "def sum_values(values):\n    return sum(values)", "idempotency_key": "same-request"}
        first = client.post("/api/submissions", json=payload).json()
        second = client.post("/api/submissions", json=payload).json()
        assert first["attempt_id"] == second["attempt_id"]
