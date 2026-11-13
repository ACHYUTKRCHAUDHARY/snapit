from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from snappe.adapters.http import create_app
from snappe.config import Settings


def test_health_endpoint() -> None:
    response = TestClient(create_app()).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint() -> None:
    response = TestClient(create_app(settings=Settings(_env_file=None))).get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_metrics_endpoint() -> None:
    response = TestClient(create_app()).get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


class BrokenDatabase:
    def check_connection(self) -> None:
        raise SQLAlchemyError("database unavailable")


def test_readiness_endpoint_reports_database_failure() -> None:
    response = TestClient(
        create_app(settings=Settings(_env_file=None), database=BrokenDatabase())
    ).get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "dependency": "database"}
