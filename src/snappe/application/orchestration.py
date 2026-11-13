"""Application orchestration across the Channel, Brain, Profile, and Actions layers."""

from dataclasses import dataclass
from typing import Protocol

from snappe.application.handover import HandoverManager
from snappe.application.profiles import ProfileRepository
from snappe.domain.brain import BrainProposal, enforce_guardrails


@dataclass(frozen=True)
class InboundMessage:
    """Normalized customer input; message text is data, never instructions."""

    business_id: str
    conversation_id: str
    text: str


class Brain(Protocol):
    def __call__(self, message: InboundMessage, profile_facts: dict[str, object]) -> BrainProposal:
        """Return a strictly validated proposal for application guardrails."""


@dataclass(frozen=True)
class ResponseResult:
    """Safe response or an explicit handover decision."""

    reply: str | None
    handover_required: bool
    reason: str | None = None


class MessageOrchestrator:
    """Apply profile, handover, and brain guardrails in a fixed order."""

    def __init__(
        self,
        profiles: ProfileRepository,
        handovers: HandoverManager,
        brain: Brain,
    ) -> None:
        self._profiles = profiles
        self._handovers = handovers
        self._brain = brain

    def handle(self, message: InboundMessage) -> ResponseResult:
        """Process one message without allowing customer text to control code."""
        if self._handovers.state(message.conversation_id).paused:
            return ResponseResult(None, True, "conversation is paused for handover")
        profile = next(
            (
                candidate
                for candidate in self._profiles.list_for_business(message.business_id)
                if candidate.active
            ),
            None,
        )
        proposal = self._brain(message, dict(profile.approved_facts) if profile else {})
        decision = enforce_guardrails(proposal, profile)
        if decision.handover_required:
            self._handovers.pause(message.conversation_id, decision.reason or "guardrail decision")
        return ResponseResult(decision.reply, decision.handover_required, decision.reason)
