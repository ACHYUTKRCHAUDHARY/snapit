# ADR 0007: Voice pipeline

- Status: Accepted
- Decision: Voice messages are handled as an adapter pipeline: verify and
  normalize the channel payload, transcribe audio through a replaceable
  speech-to-text port, then pass only the bounded transcript to the same
  application orchestration used for text messages. Voice responses are
  synthesized through a separate optional text-to-speech port.
- Rationale: Keeping speech providers outside the domain preserves the
  four-layer architecture, makes provider failures explicit, and ensures the
  same profile facts, consent rules, guardrails, and handover behavior apply
  to voice and text.
