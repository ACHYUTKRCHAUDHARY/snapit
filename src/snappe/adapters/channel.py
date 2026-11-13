"""Channel primitives for authenticated, normalized inbound events."""

import hashlib
import hmac
from dataclasses import dataclass


@dataclass(frozen=True)
class InboundEvent:
    """Normalized channel event with no provider-specific payload."""

    event_id: str
    business_id: str
    conversation_id: str
    sender_id: str
    text: str


def verify_signature(payload: bytes, signature_header: str, app_secret: str) -> bool:
    """Verify a Meta-style ``sha256=...`` signature in constant time."""
    prefix, separator, supplied = signature_header.partition("=")
    if prefix != "sha256" or not separator or not supplied:
        return False
    expected = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


class EventDeduplicator:
    """Bounded in-process event deduplication for webhook retries."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def accept(self, provider: str, event_id: str) -> bool:
        key = (provider, event_id)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True
