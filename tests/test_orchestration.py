from datetime import UTC, datetime

from snappe.adapters.profiles import InMemoryProfileRepository
from snappe.application.handover import HandoverManager
from snappe.application.orchestration import InboundMessage, MessageOrchestrator
from snappe.application.profiles import ProfileService
from snappe.domain.brain import BrainProposal


def test_orchestrator_pauses_on_ungrounded_brain_output() -> None:
    profiles = InMemoryProfileRepository()
    service = ProfileService(profiles)
    service.activate(
        "business-1",
        service.create_draft("business-1", "Acme", ("English",), {"hours": "9-5"}).version,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    handovers = HandoverManager({"operator-1"})

    def brain(message: InboundMessage, facts: dict[str, object]) -> BrainProposal:
        assert message.text == "What is the discount?"
        assert facts == {"hours": "9-5"}
        return BrainProposal("We have a discount.", frozenset({"discount"}))

    result = MessageOrchestrator(profiles, handovers, brain).handle(
        InboundMessage("business-1", "conversation-1", "What is the discount?")
    )

    assert result.handover_required is True
    assert handovers.state("conversation-1").paused is True
