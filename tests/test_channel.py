import hashlib
import hmac

from snappe.adapters.channel import EventDeduplicator, verify_signature


def test_channel_signature_verification_and_replay_deduplication() -> None:
    body = b'{"id":"event-1"}'
    signing_key = "test-signing-key"
    digest = hmac.new(signing_key.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(body, f"sha256={digest}", signing_key)
    assert not verify_signature(body, "sha1=invalid", signing_key)

    deduplicator = EventDeduplicator()
    assert deduplicator.accept("meta", "event-1")
    assert not deduplicator.accept("meta", "event-1")
    assert deduplicator.accept("other-provider", "event-1")
