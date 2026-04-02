from fastapi.testclient import TestClient

from context_router.server.app import app


client = TestClient(app)


def test_health_endpoint_returns_healthy() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "healthy"


def test_single_health_route_is_registered() -> None:
    health_routes = [route for route in app.routes if getattr(route, "path", "") == "/health"]
    assert len(health_routes) == 1


def test_tasks_endpoint_exposes_three_difficulties() -> None:
    response = client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json().get("tasks", [])
    names = {task.get("name") for task in tasks}
    assert names == {"easy", "medium", "hard"}


def test_baseline_endpoint_returns_scores_between_zero_and_one() -> None:
    response = client.post("/baseline")
    assert response.status_code == 200
    payload = response.json()
    for task_id in ("easy", "medium", "hard"):
        assert task_id in payload
        assert 0.0 <= float(payload[task_id]) <= 1.0


def test_grader_rejects_unknown_task_id() -> None:
    response = client.post(
        "/grader",
        json={"task_id": "unknown", "trajectory": []},
    )
    assert response.status_code == 422
