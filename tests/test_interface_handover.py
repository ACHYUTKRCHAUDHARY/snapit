from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from snappe.application.handover import HandoverManager
from snappe.config import Settings, get_settings
from snappe.interfaces.handover import get_handover_manager
from snappe.main import create_full_app

JWT_KEY = "test-key-that-is-at-least-32-bytes-long!"


def _make_token(user_id: str = "user-1") -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        JWT_KEY,
        algorithm="HS256",
    )


def _auth_header(user_id: str = "user-1") -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr(JWT_KEY),
    )
    app = create_full_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    manager = HandoverManager({"user-1"})
    app.dependency_overrides[get_handover_manager] = lambda: manager
    return TestClient(app)


def test_get_handover_state_default(client: TestClient) -> None:
    response = client.get("/handover/conv-default", headers=_auth_header())

    assert response.status_code == 200
    data = response.json()
    assert data["paused"] is False
    assert data["reason"] == ""


def test_pause_conversation(client: TestClient) -> None:
    response = client.post(
        "/handover/conv-pause/pause",
        json={"reason": "customer escalation"},
        headers=_auth_header(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paused"] is True
    assert data["reason"] == "customer escalation"


def test_pause_then_check_state(client: TestClient) -> None:
    client.post(
        "/handover/conv-check/pause",
        json={"reason": "needs human"},
        headers=_auth_header(),
    )

    response = client.get("/handover/conv-check", headers=_auth_header())
    assert response.status_code == 200
    assert response.json()["paused"] is True


def test_resume_paused_conversation(client: TestClient) -> None:
    client.post(
        "/handover/conv-resume/pause",
        json={"reason": "complex query"},
        headers=_auth_header(),
    )

    response = client.post(
        "/handover/conv-resume/resume",
        json={"command": "/resume conv-resume"},
        headers=_auth_header(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paused"] is False


def test_resume_rejects_unauthorized_user(client: TestClient) -> None:
    client.post(
        "/handover/conv-unauth/pause",
        json={"reason": "test"},
        headers=_auth_header(),
    )

    response = client.post(
        "/handover/conv-unauth/resume",
        json={"command": "/resume conv-unauth"},
        headers=_auth_header("unauthorized-user"),
    )

    assert response.status_code == 403


def test_resume_rejects_wrong_command(client: TestClient) -> None:
    client.post(
        "/handover/conv-wrong-cmd/pause",
        json={"reason": "test"},
        headers=_auth_header(),
    )

    response = client.post(
        "/handover/conv-wrong-cmd/resume",
        json={"command": "resume conv-wrong-cmd"},
        headers=_auth_header(),
    )

    assert response.status_code == 422


def test_handover_endpoints_require_authentication() -> None:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr(JWT_KEY),
    )
    app = create_full_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    assert client.get("/handover/conv-1").status_code == 401
    assert client.post("/handover/conv-1/pause", json={"reason": "x"}).status_code == 401
    assert client.post("/handover/conv-1/resume", json={"command": "x"}).status_code == 401
