from datetime import UTC, datetime

import pytest

from snappe.adapters.profiles import InMemoryProfileRepository
from snappe.application.profiles import ProfileService
from snappe.domain.profile import BusinessProfile, ProfileValidationError


def test_profile_requires_approval_timestamp_when_active() -> None:
    with pytest.raises(ProfileValidationError, match="approval timestamp"):
        BusinessProfile(
            business_id="business-1",
            version=1,
            display_name="Acme",
            languages=("English",),
            approved_facts={"hours": "9-5"},
            active=True,
        )


def test_service_versions_and_activates_profile() -> None:
    repository = InMemoryProfileRepository()
    service = ProfileService(repository)
    approved_at = datetime(2026, 1, 1, tzinfo=UTC)

    first = service.create_draft("business-1", "Acme", ("English",), {"hours": "9-5"})
    second = service.create_draft("business-1", "Acme updated", ("English", "Hindi"), {})
    active = service.activate("business-1", second.version, approved_at)

    assert first.version == 1
    assert second.version == 2
    assert active.active is True
    assert active.approved_at == approved_at
    assert service.active_profile("business-1") == active
    assert repository.get("business-1", first.version).active is False


def test_service_rejects_unknown_profile_version() -> None:
    with pytest.raises(ProfileValidationError, match="does not exist"):
        ProfileService(InMemoryProfileRepository()).activate("business-1", 99)
