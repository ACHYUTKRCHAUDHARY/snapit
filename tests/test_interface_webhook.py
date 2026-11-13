import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from snappe.config import Settings, get_settings
from snappe.main import create_full_app

JWT_KEY = "test-key-that-is-at-least-32-bytes-long!"
META_KEY = "meta-app-signature-secret-key-32b!"
VERIFY_TOKEN_VAL = "verify-challenge-token-string"  # noqa: S105


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


def _auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token()}"}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr(JWT_KEY),
        meta_app_secret=SecretStr(META_KEY),
        meta_verify_token=SecretStr(VERIFY_TOKEN_VAL),
    )
    app = create_full_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture
def client_no_meta() -> TestClient:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr(JWT_KEY),
    )
    app = create_full_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_webhook_verification_challenge(client: TestClient) -> None:
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN_VAL,
            "hub.challenge": "challenge-string-123",
        },
    )

    assert response.status_code == 200
    assert response.text == "challenge-string-123"


def test_webhook_verification_rejects_wrong_token(client: TestClient) -> None:
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge",
        },
    )

    assert response.status_code == 403


def test_webhook_verification_rejects_wrong_mode(client: TestClient) -> None:
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": VERIFY_TOKEN_VAL,
            "hub.challenge": "challenge",
        },
    )

    assert response.status_code == 403


def test_webhook_verification_rejects_missing_params(client: TestClient) -> None:
    response = client.get("/webhook", params={"hub.mode": "subscribe"})

    assert response.status_code == 400


def test_webhook_verification_fails_without_meta_verify_token(
    client_no_meta: TestClient,
) -> None:
    response = client_no_meta.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "anything",
            "hub.challenge": "challenge",
        },
    )

    assert response.status_code == 500


def test_webhook_receives_message_and_processes(client_no_meta: TestClient) -> None:
    client_no_meta.post(
        "/profiles/biz-webhook",
        json={"display_name": "WebhookShop", "approved_facts": {"hours": "9-5"}},
        headers=_auth_header(),
    )
    client_no_meta.post(
        "/profiles/biz-webhook/1/activate",
        json={},
        headers=_auth_header(),
    )

    response = client_no_meta.post(
        "/webhook",
        json={
            "event_id": "evt-unique-1",
            "business_id": "biz-webhook",
            "conversation_id": "conv-1",
            "sender_id": "sender-1",
            "text": "What are your hours?",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] is not None or data["handover_required"] is True


def test_webhook_deduplicates_events(client_no_meta: TestClient) -> None:
    payload = {
        "event_id": "evt-dedup-test",
        "business_id": "biz-dedup",
        "conversation_id": "conv-dedup",
        "sender_id": "sender-dedup",
        "text": "hello",
    }

    first_response = client_no_meta.post("/webhook", json=payload)
    second_response = client_no_meta.post("/webhook", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["reason"] == "duplicate event"


def test_webhook_validates_signature_when_secret_configured(
    client: TestClient,
) -> None:
    payload_body = json.dumps(
        {
            "event_id": "evt-sig-test",
            "business_id": "biz-sig",
            "conversation_id": "conv-sig",
            "sender_id": "sender-sig",
            "text": "hi",
        }
    ).encode()
    digest = hmac.new(META_KEY.encode(), payload_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={digest}",
        },
    )

    assert response.status_code == 200


def test_webhook_rejects_invalid_signature(client: TestClient) -> None:
    payload_body = json.dumps(
        {
            "event_id": "evt-bad-sig",
            "business_id": "biz-bad-sig",
            "conversation_id": "conv-bad-sig",
            "sender_id": "sender-bad-sig",
            "text": "hello",
        }
    ).encode()

    response = client.post(
        "/webhook",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )

    assert response.status_code == 401
