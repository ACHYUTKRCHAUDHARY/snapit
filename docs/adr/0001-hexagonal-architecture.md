# ADR 0001: Hexagonal architecture

- Status: Accepted
- Decision: Keep domain and application use cases independent of adapters,
  exposing integrations through typed Protocol ports.
- Rationale: WhatsApp, LLM, calendar, and persistence vendors can change
  without rewriting the replier engine or its tests.
