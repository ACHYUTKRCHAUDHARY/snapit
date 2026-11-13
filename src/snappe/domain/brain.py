"""Validated brain proposals and code-enforced response guardrails."""

from dataclasses import dataclass
from typing import Final

from snappe.domain.profile import BusinessProfile

MAX_REPLY_LENGTH: Final[int] = 1000


class GuardrailViolation(ValueError):
    """Raised when a brain proposal cannot be safely sent."""


@dataclass(frozen=True)
class BrainProposal:
    """A response proposed by a brain adapter."""

    reply: str
    cited_fact_keys: frozenset[str] = frozenset()
    intent: str = "unknown"
    requires_handover: bool = False


@dataclass(frozen=True)
class GuardrailDecision:
    """The application decision for a brain proposal."""

    reply: str | None
    handover_required: bool
    reason: str | None = None


def enforce_guardrails(
    proposal: BrainProposal,
    profile: BusinessProfile | None,
) -> GuardrailDecision:
    """Allow only concise proposals grounded in an active business profile."""
    if profile is None or not profile.active:
        return GuardrailDecision(None, True, "no active profile")
    if proposal.requires_handover:
        return GuardrailDecision(None, True, "brain requested handover")
    reply = proposal.reply.strip()
    if not reply:
        return GuardrailDecision(None, True, "empty brain response")
    if len(reply) > MAX_REPLY_LENGTH:
        return GuardrailDecision(None, True, "response exceeds maximum length")
    unknown_facts = proposal.cited_fact_keys.difference(profile.approved_facts)
    if unknown_facts:
        return GuardrailDecision(None, True, "response cites unapproved facts")
    return GuardrailDecision(reply, False)
