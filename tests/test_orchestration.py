from datetime import UTC, datetime

import pytest

from snappe.adapters.profiles import InMemoryProfileRepository
from snappe.adapters.whatsapp import FakeWhatsAppSender
from snappe.application.handover import HandoverManager
from snappe.application.orchestration import (
    InboundMessage,
    MessageOrchestrator,
    MessageSendError,
)
from snappe.application.profiles import ProfileService
from snappe.domain.brain import BrainProposal


def _build_orchestrator(
    brain_response: BrainProposal,
    sender: FakeWhatsAppSender,
) -> tuple[MessageOrchestrator, HandoverManager]:
    profiles = InMemoryProfileRepository()
    service = ProfileService(profiles)
    service.activate(
        "business-1",
        service.create_draft("business-1", "Acme", ("English",), {"hours": "9-5"}).version,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    handovers = HandoverManager({"operator-1"})

    def brain(message: InboundMessage, facts: dict[str, object]) -> BrainProposal:
        return brain_response

    return MessageOrchestrator(profiles, handovers, brain, sender), handovers


def test_orchestrator_pauses_on_ungrounded_brain_output() -> None:
    sender = FakeWhatsAppSender()
    orchestrator, handovers = _build_orchestrator(
        BrainProposal("We have a discount.", frozenset({"discount"})), sender
    )

    result = orchestrator.handle(
        InboundMessage("business-1", "conversation-1", "sender-1", "What is the discount?")
    )

    assert result.handover_required is True
    assert handovers.state("conversation-1").paused is True
    assert sender.sent == []  # never sent — guardrail blocked it


def test_orchestrator_delivers_grounded_reply() -> None:
    sender = FakeWhatsAppSender()
    orchestrator, _handovers = _build_orchestrator(
        BrainProposal("We are open 9-5.", frozenset({"hours"})), sender
    )

    result = orchestrator.handle(
        InboundMessage("business-1", "conv-2", "sender-wa-99", "When are you open?")
    )

    assert result.handover_required is False
    assert result.reply == "We are open 9-5."
    assert result.delivered is True
    assert sender.sent == [("sender-wa-99", "We are open 9-5.")]


def test_orchestrator_records_failed_delivery() -> None:
    sender = FakeWhatsAppSender(raise_error=MessageSendError("network down"))
    orchestrator, _ = _build_orchestrator(
        BrainProposal("We are open 9-5.", frozenset({"hours"})), sender
    )

    result = orchestrator.handle(InboundMessage("business-1", "conv-3", "sender-fail", "Hours?"))

    # Reply was valid but could not be delivered — no handover, delivered=False
    assert result.handover_required is False
    assert result.reply == "We are open 9-5."
    assert result.delivered is False


def test_orchestrator_skips_send_when_paused() -> None:
    sender = FakeWhatsAppSender()
    orchestrator, handovers = _build_orchestrator(
        BrainProposal("We are open 9-5.", frozenset({"hours"})), sender
    )
    handovers.pause("conv-paused", "pre-paused by operator")

    result = orchestrator.handle(InboundMessage("business-1", "conv-paused", "sender-99", "hi"))

    assert result.handover_required is True
    assert sender.sent == []


@pytest.mark.parametrize("bad_reply", ["", " ", "\t\n"])
def test_orchestrator_handovers_on_empty_brain_reply(bad_reply: str) -> None:
    sender = FakeWhatsAppSender()
    orchestrator, _handovers = _build_orchestrator(
        BrainProposal(bad_reply, frozenset({"hours"})), sender
    )

    result = orchestrator.handle(InboundMessage("business-1", "conv-empty", "sender-x", "hi"))

    assert result.handover_required is True
    assert sender.sent == []
