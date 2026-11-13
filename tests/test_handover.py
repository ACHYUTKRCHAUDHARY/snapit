import pytest

from snappe.application.handover import HandoverManager


def test_handover_stays_paused_until_authorized_exact_resume() -> None:
    manager = HandoverManager({"operator-1"})
    manager.pause("conversation-1", "unknown policy")

    with pytest.raises(PermissionError):
        manager.resume("conversation-1", "customer-1", "/resume conversation-1")
    with pytest.raises(ValueError, match="exact explicit"):
        manager.resume("conversation-1", "operator-1", "resume conversation-1")

    state = manager.resume("conversation-1", "operator-1", "/resume conversation-1")
    assert state.paused is False
    assert manager.state("conversation-1").paused is False
