"""Application orchestration across the Channel, Brain, Profile, and Actions layers."""

from dataclasses import dataclass
from typing import Protocol

from snappe.application.handover import HandoverManager
from snappe.application.profiles import ProfileRepository
from snappe.domain.brain import BrainProposal, enforce_guardrails


class MessageSendError(RuntimeError):
    """Raised when a reply cannot be delivered to the WhatsApp channel."""


@dataclass(frozen=True)
class InboundMessage:
    """Normalized customer input; message text is data, never instructions."""

    business_id: str
    conversation_id: str
    sender_id: str
    text: str


class Brain(Protocol):
    def __call__(self, message: InboundMessage, profile_facts: dict[str, object]) -> BrainProposal:
        """Return a strictly validated proposal for application guardrails."""


class WhatsAppSender(Protocol):
    """Port for sending outbound WhatsApp text messages."""

    def send_reply(self, to: str, text: str) -> None:
        """Deliver *text* to the WhatsApp number identified by *to*.

        Raises :exc:`MessageSendError` on any delivery failure.
        """


@dataclass(frozen=True)
class ResponseResult:
    """Safe response or an explicit handover decision."""

    reply: str | None
    handover_required: bool
    reason: str | None = None
    delivered: bool = False


class MessageOrchestrator:
    """Apply profile, handover, and brain guardrails in a fixed order.

    After a reply passes all guardrails it is dispatched via *sender*.
    Delivery failures are recorded in :attr:`ResponseResult.delivered` but
    never trigger a second handover — the message was validated and the
    transient send error is surfaced to the caller for retry decisions.
    """

    def __init__(
        self,
        profiles: ProfileRepository,
        handovers: HandoverManager,
        brain: Brain,
        sender: WhatsAppSender,
    ) -> None:
        self._profiles = profiles
        self._handovers = handovers
        self._brain = brain
        self._sender = sender

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
            return ResponseResult(None, True, decision.reason)
        # Guardrails passed — attempt delivery.
        reply = decision.reply
        if reply is None:
            return ResponseResult(None, True, "empty reply")
        delivered = False
        try:
            self._sender.send_reply(message.sender_id, reply)
            delivered = True
        except MessageSendError:
            # Surface the delivery failure but keep the reply visible to the
            # caller so it can log, retry, or escalate without losing the text.
            delivered = False
        return ResponseResult(reply, False, None, delivered)
