"""Data minimization, masking, consent, and retention primitives."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

_PHONE_SUFFIX_LENGTH = 4


def hash_phone(phone: str, salt: str = "") -> str:
    """Return a deterministic one-way SHA-256 hash of a normalized phone number."""
    normalized = "".join(
        character for character in phone if character.isdigit() or character == "+"
    )
    salted = f"{salt}:{normalized}" if salt else normalized
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def mask_phone(phone: str) -> str:
    """Return a log-safe phone representation without exposing the full number."""
    normalized = "".join(
        character for character in phone if character.isdigit() or character == "+"
    )
    if len(normalized) <= _PHONE_SUFFIX_LENGTH:
        return "***"
    return f"{'*' * (len(normalized) - _PHONE_SUFFIX_LENGTH)}{normalized[-_PHONE_SUFFIX_LENGTH:]}"


@dataclass(frozen=True)
class AuditEvent:
    """Minimal audit record; message bodies and full phone numbers are excluded."""

    event_type: str
    actor_user_id: str | None
    business_id: str | None
    metadata: dict[str, str]
    created_at: datetime


class RetentionStore(Protocol):
    def purge_before(self, cutoff: datetime) -> int:
        """Delete records older than the cutoff and return the count."""


class CustomerDataStore(Protocol):
    def purge_customer_data(self, business_id: str, customer_id: str) -> int:
        """Purge all data associated with a customer for GDPR/DPDP compliance."""


def purge_expired(store: RetentionStore, retention_days: int, now: datetime | None = None) -> int:
    """Apply the configured retention period to a persistence port."""
    if retention_days <= 0:
        raise ValueError("retention_days must be greater than zero")
    timestamp = now or datetime.now(UTC)
    return store.purge_before(timestamp - timedelta(days=retention_days))
