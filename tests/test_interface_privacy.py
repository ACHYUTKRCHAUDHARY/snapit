"""Tests for data protection and privacy interfaces."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from snappe.adapters.database import Database
from snappe.adapters.models import MessageModel
from snappe.adapters.sql_conversations import SQLConversationRepository
from snappe.config import Settings, get_settings
from snappe.interfaces.webhook import get_conversation_repository
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


def _auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token()}"}


@pytest.fixture
def privacy_client(tmp_path) -> tuple[TestClient, SQLConversationRepository]:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'privacy_test.db'}",
        supabase_jwt_secret=SecretStr(JWT_KEY),
        retention_days=30,
    )
    db = Database(settings)
    db.create_tables()
    repo = SQLConversationRepository(db)
    app = create_full_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_conversation_repository] = lambda: repo
    return TestClient(app), repo


def test_retention_purge_endpoint(
    privacy_client: tuple[TestClient, SQLConversationRepository],
) -> None:
    client, repo = privacy_client

    # Insert an old message (40 days old) and a recent message
    repo.get_or_create("c1", "b1", "u1")
    old_msg = repo.record_message("b1", "c1", "inbound", "old text", provider_message_id="p1")
    # Manually update created_at for the old message
    with repo._session_factory() as session:
        m = session.get(MessageModel, old_msg.id)
        if m is not None:
            m.created_at = datetime.now(UTC) - timedelta(days=40)
            session.commit()

    repo.record_message("b1", "c1", "inbound", "recent text", provider_message_id="p2")

    response = client.post("/privacy/retention/purge", headers=_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert data["retention_days"] == 30
    assert data["purged_messages_count"] == 1

    remaining = repo.list_messages("c1")
    assert len(remaining) == 1
    assert remaining[0].content == "recent text"


def test_customer_data_purge_endpoint(
    privacy_client: tuple[TestClient, SQLConversationRepository],
) -> None:
    client, repo = privacy_client

    repo.get_or_create("c-cust1", "biz-erase", "target-customer")
    repo.record_message("biz-erase", "c-cust1", "inbound", "cust msg 1", provider_message_id="m1")
    repo.record_message("biz-erase", "c-cust1", "outbound", "bot msg 1", provider_message_id="m2")

    # Another customer's conversation
    repo.get_or_create("c-cust2", "biz-erase", "other-customer")
    repo.record_message("biz-erase", "c-cust2", "inbound", "other msg", provider_message_id="m3")

    response = client.post(
        "/privacy/customers/biz-erase/purge",
        json={"customer_id": "target-customer"},
        headers=_auth_header(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["business_id"] == "biz-erase"
    assert data["customer_id"] == "target-customer"
    assert data["purged_messages_count"] == 2

    # Verify target customer messages are gone
    assert repo.list_messages("c-cust1") == []
    # Other customer is intact
    assert len(repo.list_messages("c-cust2")) == 1


def test_privacy_endpoints_require_authentication(
    privacy_client: tuple[TestClient, SQLConversationRepository],
) -> None:
    client, _ = privacy_client
    assert client.post("/privacy/retention/purge").status_code == 401
    assert client.post("/privacy/customers/b1/purge", json={"customer_id": "c1"}).status_code == 401
