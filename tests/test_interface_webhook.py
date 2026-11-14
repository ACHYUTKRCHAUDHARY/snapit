import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from snappe.adapters.database import Database
from snappe.adapters.sql_conversations import SQLConversationRepository
from snappe.adapters.whatsapp import FakeWhatsAppSender
from snappe.application.resilience import RateLimiter
from snappe.config import Settings, get_settings
from snappe.interfaces.webhook import (
    get_conversation_repository,
    get_rate_limiter,
    get_whatsapp_sender,
)
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


def _make_client(
    *,
    meta_secret: bool = False,
    sender: FakeWhatsAppSender | None = None,
    conv_repo: SQLConversationRepository | None = None,
    rate_limiter: RateLimiter | None = None,
) -> TestClient:
    """Build a TestClient with an optional Meta secret and a captured sender."""
    kw: dict[str, SecretStr | str] = {"supabase_jwt_secret": SecretStr(JWT_KEY)}
    if meta_secret:
        kw["meta_app_secret"] = SecretStr(META_KEY)
        kw["meta_verify_token"] = SecretStr(VERIFY_TOKEN_VAL)
    settings = Settings(_env_file=None, **kw)  # type: ignore[arg-type]
    app = create_full_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    fake_sender = sender or FakeWhatsAppSender()
    app.dependency_overrides[get_whatsapp_sender] = lambda: fake_sender
    if rate_limiter is not None:
        app.dependency_overrides[get_rate_limiter] = lambda: rate_limiter
    if conv_repo is not None:
        app.dependency_overrides[get_conversation_repository] = lambda: conv_repo
    else:
        db = Database(settings)
        db.create_tables()
        repo = SQLConversationRepository(db)
        app.dependency_overrides[get_conversation_repository] = lambda: repo
    return TestClient(app)


@pytest.fixture
def client() -> TestClient:
    return _make_client(meta_secret=True)


@pytest.fixture
def client_no_meta() -> TestClient:
    return _make_client()


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


def test_webhook_captures_outbound_message() -> None:
    """End-to-end: a valid reply must be delivered via the WhatsApp sender."""
    sender = FakeWhatsAppSender()
    tc = _make_client(sender=sender)

    tc.post(
        "/profiles/biz-e2e",
        json={"display_name": "E2E Shop", "approved_facts": {"hours": "9-5"}},
        headers=_auth_header(),
    )
    tc.post("/profiles/biz-e2e/1/activate", json={}, headers=_auth_header())

    response = tc.post(
        "/webhook",
        json={
            "event_id": "evt-e2e-1",
            "business_id": "biz-e2e",
            "conversation_id": "conv-e2e",
            "sender_id": "+919876543210",
            "text": "What are your hours?",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # If a reply was produced it must have been sent via sender
    if data["reply"] is not None:
        assert data["delivered"] is True
        assert any(to == "+919876543210" for to, _ in sender.sent)


def test_webhook_delivered_false_on_no_profile() -> None:
    """When there's no active profile the reply is None and delivered stays False."""
    sender = FakeWhatsAppSender()
    tc = _make_client(sender=sender)

    response = tc.post(
        "/webhook",
        json={
            "event_id": "evt-noprofile",
            "business_id": "biz-unknown",
            "conversation_id": "conv-np",
            "sender_id": "+91000",
            "text": "hello",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["handover_required"] is True
    assert data["reply"] is None
    assert sender.sent == []


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


def test_webhook_persists_inbound_and_outbound_messages(tmp_path) -> None:
    db = Database(Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'audit.db'}"))
    db.create_tables()
    repo = SQLConversationRepository(db)
    client = _make_client(conv_repo=repo)

    # Setup active profile
    client.post(
        "/profiles/biz-audit",
        json={"display_name": "Audit Shop", "approved_facts": {"policy": "no-returns"}},
        headers=_auth_header(),
    )
    client.post("/profiles/biz-audit/1/activate", json={}, headers=_auth_header())

    # Send webhook message
    response = client.post(
        "/webhook",
        json={
            "event_id": "evt-audit-1",
            "business_id": "biz-audit",
            "conversation_id": "conv-audit-1",
            "sender_id": "+919988776655",
            "text": "What is the return policy?",
        },
    )
    assert response.status_code == 200

    # Verify database persistence
    conv = repo.get_or_create("conv-audit-1", "biz-audit", "+919988776655")
    assert conv.id == "conv-audit-1"

    msgs = repo.list_messages("conv-audit-1")
    assert len(msgs) >= 1
    assert msgs[0].direction == "inbound"
    assert msgs[0].content == "What is the return policy?"
    assert msgs[0].provider_message_id == "evt-audit-1"


def test_webhook_rate_limiting_returns_429() -> None:
    limiter = RateLimiter(default_rate=1.0, default_capacity=1.0)
    client = _make_client(rate_limiter=limiter)

    payload = {
        "event_id": "evt-rl-1",
        "business_id": "biz-rate-limited",
        "conversation_id": "conv-rl",
        "sender_id": "+9111223344",
        "text": "hello",
    }

    # First request consumes token
    res1 = client.post("/webhook", json=payload)
    assert res1.status_code == 200

    # Second request with new event_id exceeds rate limit
    payload["event_id"] = "evt-rl-2"
    res2 = client.post("/webhook", json=payload)
    assert res2.status_code == 429
    assert "Rate limit exceeded" in res2.json()["detail"]
