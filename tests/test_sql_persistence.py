"""Tests for SQL repositories (SQLProfileRepository, SQLConversationRepository) and models."""

from datetime import UTC, datetime

import pytest

from snappe.adapters.database import Database
from snappe.adapters.sql_conversations import SQLConversationRepository
from snappe.adapters.sql_profiles import SQLProfileRepository
from snappe.application.profiles import ProfileService
from snappe.config import Settings
from snappe.domain.profile import BusinessProfile


@pytest.fixture
def test_db(tmp_path) -> Database:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'test_persistence.db'}",
    )
    db = Database(settings)
    db.create_tables()
    try:
        yield db
    finally:
        db.dispose()


def test_sql_profile_repository_crud(test_db: Database) -> None:
    repo = SQLProfileRepository(test_db)
    service = ProfileService(repo)

    # 1. Create draft
    draft = service.create_draft(
        business_id="biz-101",
        display_name="Cafe Latte",
        languages=("English", "Hindi"),
        approved_facts={"wifi": "free", "rating": 4.8},
    )
    assert draft.version == 1
    assert draft.active is False
    assert draft.approved_at is None

    # 2. Get profile
    fetched = repo.get("biz-101", 1)
    assert fetched is not None
    assert fetched.display_name == "Cafe Latte"
    assert fetched.languages == ("English", "Hindi")
    assert fetched.approved_facts["wifi"] == "free"

    # Nonexistent
    assert repo.get("biz-101", 999) is None

    # 3. Create v2
    draft_v2 = service.create_draft(
        business_id="biz-101",
        display_name="Cafe Latte Premium",
        languages=("English",),
        approved_facts={"wifi": "superfast"},
    )
    assert draft_v2.version == 2

    # 4. Activate v2
    activated = service.activate("biz-101", 2, datetime(2026, 1, 1, tzinfo=UTC))
    assert activated.active is True
    assert activated.approved_at is not None

    active_profile = service.active_profile("biz-101")
    assert active_profile is not None
    assert active_profile.version == 2

    # Verify v1 is inactive
    v1 = repo.get("biz-101", 1)
    assert v1 is not None
    assert v1.active is False

    # 5. List for business
    all_profiles = list(repo.list_for_business("biz-101"))
    assert len(all_profiles) == 2
    assert all_profiles[0].version == 1
    assert all_profiles[1].version == 2


def test_sql_profile_repository_update_existing(test_db: Database) -> None:
    repo = SQLProfileRepository(test_db)
    profile = BusinessProfile(
        business_id="biz-update",
        version=1,
        display_name="Initial",
        languages=("English",),
        approved_facts={"a": 1},
        active=False,
    )
    repo.save(profile)

    updated_profile = BusinessProfile(
        business_id="biz-update",
        version=1,
        display_name="Updated",
        languages=("English", "Spanish"),
        approved_facts={"a": 2},
        active=False,
    )
    repo.save(updated_profile)

    fetched = repo.get("biz-update", 1)
    assert fetched is not None
    assert fetched.display_name == "Updated"
    assert fetched.approved_facts["a"] == 2


def test_sql_conversation_repository(test_db: Database) -> None:
    repo = SQLConversationRepository(test_db)

    # 1. get_or_create
    conv = repo.get_or_create("conv-1", "biz-1", "cust-1")
    assert conv.id == "conv-1"
    assert conv.business_id == "biz-1"
    assert conv.status == "active"
    assert conv.handover_reason is None

    # Second call returns existing
    conv_repeat = repo.get_or_create("conv-1", "biz-1", "cust-1")
    assert conv_repeat.id == "conv-1"

    # 2. record inbound message
    msg_in = repo.record_message(
        business_id="biz-1",
        conversation_id="conv-1",
        direction="inbound",
        content="Hello!",
        provider_message_id="wamid-123",
        intent="greeting",
    )
    assert msg_in.direction == "inbound"
    assert msg_in.content == "Hello!"
    assert msg_in.provider_message_id == "wamid-123"
    assert msg_in.intent == "greeting"

    # 3. record outbound message
    msg_out = repo.record_message(
        business_id="biz-1",
        conversation_id="conv-1",
        direction="outbound",
        content="Welcome to Cafe Latte!",
        delivery_status="delivered",
    )
    assert msg_out.direction == "outbound"
    assert msg_out.delivery_status == "delivered"

    # 4. list_messages
    messages = repo.list_messages("conv-1")
    assert len(messages) == 2
    assert messages[0].content == "Hello!"
    assert messages[1].content == "Welcome to Cafe Latte!"

    # 5. update_status to handover
    repo.update_status("conv-1", "handover", "guardrail triggered")
    updated_conv = repo.get_or_create("conv-1", "biz-1", "cust-1")
    assert updated_conv.status == "handover"
    assert updated_conv.handover_reason == "guardrail triggered"

