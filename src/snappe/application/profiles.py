"""Business profile use cases and persistence ports."""

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from snappe.domain.profile import ApprovedFacts, BusinessProfile, ProfileValidationError


class ProfileRepository(Protocol):
    """Persistence port for versioned business profiles."""

    def save(self, profile: BusinessProfile) -> None:
        """Persist a profile version."""

    def get(self, business_id: str, version: int) -> BusinessProfile | None:
        """Return one profile version, if it exists."""

    def list_for_business(self, business_id: str) -> Iterable[BusinessProfile]:
        """Return all profile versions for a business."""

    def set_active(self, business_id: str, version: int) -> None:
        """Mark exactly one profile version active."""


class ProfileService:
    """Create and approve business profiles without adapter dependencies."""

    def __init__(self, repository: ProfileRepository) -> None:
        self._repository = repository

    def create_draft(
        self,
        business_id: str,
        display_name: str,
        languages: tuple[str, ...],
        approved_facts: ApprovedFacts,
    ) -> BusinessProfile:
        """Create the next inactive profile version for a business."""
        versions = [profile.version for profile in self._repository.list_for_business(business_id)]
        profile = BusinessProfile(
            business_id=business_id,
            version=max(versions, default=0) + 1,
            display_name=display_name,
            languages=languages,
            approved_facts=approved_facts,
        )
        self._repository.save(profile)
        return profile

    def activate(
        self,
        business_id: str,
        version: int,
        approved_at: datetime | None = None,
    ) -> BusinessProfile:
        """Approve a draft and make it the sole active profile."""
        profile = self._repository.get(business_id, version)
        if profile is None:
            raise ProfileValidationError("profile version does not exist")
        active_profile = profile.activate(approved_at)
        self._repository.set_active(business_id, version)
        self._repository.save(active_profile)
        return active_profile

    def active_profile(self, business_id: str) -> BusinessProfile | None:
        """Return the currently approved profile for a business."""
        return next(
            (
                profile
                for profile in self._repository.list_for_business(business_id)
                if profile.active
            ),
            None,
        )
