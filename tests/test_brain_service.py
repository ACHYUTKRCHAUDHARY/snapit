import json

from snappe.adapters.llm import FakeLLMClient
from snappe.application.brain import (
    BrainService,
    LLMUnavailable,
    build_user_prompt,
    parse_brain_response,
)
from snappe.application.orchestration import InboundMessage


def test_build_user_prompt_encapsulates_untrusted_customer_message() -> None:
    message = InboundMessage("biz-1", "conv-1", "What are your hours?")
    facts = {"hours": "9am-5pm", "phone": "555-0199"}

    prompt = build_user_prompt(message, facts)

    assert "Approved Facts:" in prompt
    assert '"hours": "9am-5pm"' in prompt
    assert "<customer_message>\nWhat are your hours?\n</customer_message>" in prompt


def test_parse_brain_response_handles_clean_and_fenced_json() -> None:
    payload = json.dumps(
        {
            "reply": "We are open 9am-5pm.",
            "cited_fact_keys": ["hours"],
            "intent": "hours_inquiry",
            "requires_handover": False,
        }
    )

    clean_proposal = parse_brain_response(payload)
    assert clean_proposal.reply == "We are open 9am-5pm."
    assert clean_proposal.cited_fact_keys == frozenset({"hours"})
    assert clean_proposal.requires_handover is False

    fenced_proposal = parse_brain_response(f"```json\n{payload}\n```")
    assert fenced_proposal.reply == "We are open 9am-5pm."
    assert fenced_proposal.cited_fact_keys == frozenset({"hours"})


def test_parse_brain_response_fails_safe_on_malformed_json() -> None:
    proposal = parse_brain_response("Not JSON at all!")
    assert proposal.reply == ""
    assert proposal.requires_handover is True
    assert proposal.intent == "malformed_json"


def test_parse_brain_response_fails_safe_on_schema_violations() -> None:
    assert parse_brain_response('["not", "a", "dict"]').intent == "invalid_structure"
    assert parse_brain_response('{"reply": 123}').intent == "schema_violation"
    assert parse_brain_response('{"reply": "hi", "cited_fact_keys": "not_a_list"}').intent == (
        "schema_violation"
    )


def test_brain_service_returns_proposal_from_llm() -> None:
    llm = FakeLLMClient(
        default_response=json.dumps(
            {
                "reply": "Yes, our hours are 9-5.",
                "cited_fact_keys": ["hours"],
                "intent": "hours_inquiry",
                "requires_handover": False,
            }
        )
    )
    brain = BrainService(llm)
    message = InboundMessage("biz-1", "conv-1", "Are you open?")

    proposal = brain(message, {"hours": "9-5"})

    assert proposal.reply == "Yes, our hours are 9-5."
    assert proposal.cited_fact_keys == frozenset({"hours"})
    assert proposal.requires_handover is False
    assert len(llm.history) == 1


def test_brain_service_fails_safe_to_handover_on_llm_outage() -> None:
    llm = FakeLLMClient(raise_error=LLMUnavailable("Network timeout"))
    brain = BrainService(llm)
    message = InboundMessage("biz-1", "conv-1", "Are you open?")

    proposal = brain(message, {"hours": "9-5"})

    assert proposal.reply == ""
    assert proposal.requires_handover is True
    assert proposal.intent == "outage_fallback"


def test_brain_service_fails_safe_on_timeout_error() -> None:
    llm = FakeLLMClient(raise_error=TimeoutError("Request timed out"))
    brain = BrainService(llm)
    message = InboundMessage("biz-1", "conv-1", "Hello")

    proposal = brain(message, {})

    assert proposal.reply == ""
    assert proposal.requires_handover is True
    assert proposal.intent == "outage_fallback"
