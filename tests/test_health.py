from fastapi.testclient import TestClient

from snappe.adapters.http import create_app


def test_health_endpoint() -> None:
    response = TestClient(create_app()).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint() -> None:
    response = TestClient(create_app()).get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_metrics_endpoint() -> None:
    response = TestClient(create_app()).get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
