# ADR 0005: LLM behind a port

- Status: Accepted
- Decision: The brain depends on an `LLMClient` Protocol, with provider adapters
  selected by configuration. The initial configured provider is Gemini.
- Rationale: Provider choice, retries, timeouts, and a deterministic fake must
  not leak into business rules.
