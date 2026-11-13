from datetime import UTC, datetime

from snappe.domain.brain import BrainProposal, enforce_guardrails
from snappe.domain.profile import BusinessProfile


def active_profile() -> BusinessProfile:
    return BusinessProfile(
        business_id="business-1",
        version=1,
        display_name="Acme",
        languages=("English",),
        approved_facts={"hours": "9-5"},
        active=True,
        approved_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_guardrails_allow_only_approved_facts() -> None:
    decision = enforce_guardrails(
        BrainProposal("We are open 9-5.", frozenset({"hours"})),
        active_profile(),
    )

    assert decision.reply == "We are open 9-5."
    assert decision.handover_required is False


def test_guardrails_handover_unknown_facts_and_untrusted_brain_request() -> None:
    unknown = enforce_guardrails(
        BrainProposal("We offer a discount.", frozenset({"discount"})),
        active_profile(),
    )
    requested = enforce_guardrails(
        BrainProposal("Contact our team.", requires_handover=True),
        active_profile(),
    )

    assert unknown.handover_required is True
    assert requested.handover_required is True


def test_guardrails_require_active_profile_and_bounded_reply() -> None:
    profile = active_profile()
    inactive = BusinessProfile(
        business_id=profile.business_id,
        version=profile.version,
        display_name=profile.display_name,
        languages=profile.languages,
        approved_facts=profile.approved_facts,
    )

    assert enforce_guardrails(BrainProposal("hello"), inactive).handover_required is True
    assert enforce_guardrails(BrainProposal("x" * 1001), profile).handover_required is True
