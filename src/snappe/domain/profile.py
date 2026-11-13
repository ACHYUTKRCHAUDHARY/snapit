"""Business profile domain entities and validation."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Final

type ApprovedFact = str | int | float | bool
type ApprovedFacts = Mapping[str, ApprovedFact]
_DEFAULT_LANGUAGE: Final[str] = "English"


class ProfileValidationError(ValueError):
    """Raised when a business profile violates domain rules."""


@dataclass(frozen=True)
class BusinessProfile:
    """A versioned set of facts approved for customer-facing responses."""

    business_id: str
    version: int
    display_name: str
    languages: tuple[str, ...]
    approved_facts: ApprovedFacts
    active: bool = False
    approved_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.business_id.strip():
            raise ProfileValidationError("business_id is required")
        if self.version <= 0:
            raise ProfileValidationError("version must be greater than zero")
        if not self.display_name.strip():
            raise ProfileValidationError("display_name is required")
        if not self.languages or any(not language.strip() for language in self.languages):
            raise ProfileValidationError("at least one non-empty language is required")
        if len(set(self.languages)) != len(self.languages):
            raise ProfileValidationError("languages must be unique")
        if any(not key.strip() for key in self.approved_facts):
            raise ProfileValidationError("approved fact keys must be non-empty")
        if self.active and self.approved_at is None:
            raise ProfileValidationError("an active profile must have an approval timestamp")
        if self.approved_at is not None and self.approved_at.tzinfo is None:
            raise ProfileValidationError("approved_at must include a timezone")
        object.__setattr__(self, "display_name", self.display_name.strip())
        object.__setattr__(
            self,
            "languages",
            tuple(language.strip() for language in self.languages),
        )
        object.__setattr__(self, "approved_facts", MappingProxyType(dict(self.approved_facts)))

    def activate(self, approved_at: datetime | None = None) -> "BusinessProfile":
        """Return this profile marked as approved and active."""
        timestamp = approved_at or datetime.now(UTC)
        if timestamp.tzinfo is None:
            raise ProfileValidationError("approved_at must include a timezone")
        return BusinessProfile(
            business_id=self.business_id,
            version=self.version,
            display_name=self.display_name,
            languages=self.languages,
            approved_facts=self.approved_facts,
            active=True,
            approved_at=timestamp,
        )
