from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from snappe.adapters.profiles import InMemoryProfileRepository
from snappe.application.profiles import ProfileService
from snappe.config import Settings, get_settings
from snappe.interfaces.profiles import get_profile_service
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
    repository = InMemoryProfileRepository()
    service = ProfileService(repository)
    app = create_full_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_profile_service] = lambda: service
    return TestClient(app)


def test_create_profile_draft(client: TestClient) -> None:
    response = client.post(
        "/profiles/biz-create",
        json={
            "display_name": "Acme",
            "languages": ["English"],
            "approved_facts": {"hours": "9-5"},
        },
        headers=_auth_header(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["business_id"] == "biz-create"
    assert data["version"] >= 1
    assert data["display_name"] == "Acme"
    assert data["active"] is False


def test_list_profiles(client: TestClient) -> None:
    client.post(
        "/profiles/biz-list",
        json={"display_name": "Shop A", "approved_facts": {"open": True}},
        headers=_auth_header(),
    )
    client.post(
        "/profiles/biz-list",
        json={"display_name": "Shop A v2", "approved_facts": {"open": False}},
        headers=_auth_header(),
    )

    response = client.get("/profiles/biz-list", headers=_auth_header())
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) >= 2


def test_activate_profile(client: TestClient) -> None:
    client.post(
        "/profiles/biz-activate",
        json={"display_name": "Shop B", "approved_facts": {"phone": "123"}},
        headers=_auth_header(),
    )

    response = client.post(
        "/profiles/biz-activate/1/activate",
        json={},
        headers=_auth_header(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    assert data["approved_at"] is not None


def test_get_active_profile(client: TestClient) -> None:
    client.post(
        "/profiles/biz-active",
        json={"display_name": "Shop C", "approved_facts": {"size": "small"}},
        headers=_auth_header(),
    )
    client.post(
        "/profiles/biz-active/1/activate",
        json={},
        headers=_auth_header(),
    )

    response = client.get("/profiles/biz-active/active", headers=_auth_header())
    assert response.status_code == 200
    assert response.json()["active"] is True


def test_get_active_profile_returns_404_when_none_exists(client: TestClient) -> None:
    response = client.get("/profiles/nonexistent-biz/active", headers=_auth_header())
    assert response.status_code == 404
    assert response.json()["detail"] == "no active profile"


def test_activate_unknown_version_returns_422(client: TestClient) -> None:
    response = client.post(
        "/profiles/biz-unknown/99/activate",
        json={},
        headers=_auth_header(),
    )
    assert response.status_code == 422


def test_create_profile_validation_error_returns_422(client: TestClient) -> None:
    response = client.post(
        "/profiles/biz-invalid",
        json={"display_name": "   ", "approved_facts": {}},
        headers=_auth_header(),
    )
    assert response.status_code == 422


def test_profile_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/profiles/test-auth").status_code == 401
    assert client.post("/profiles/test-auth", json={"display_name": "X"}).status_code == 401
