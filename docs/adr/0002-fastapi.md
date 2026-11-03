# ADR 0002: FastAPI HTTP boundary

- Status: Accepted
- Decision: Use FastAPI for the webhook and operational HTTP endpoints.
- Rationale: It provides typed request handling, async support, and a small
  surface for the walking skeleton and future webhook contracts.
