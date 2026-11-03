# ADR 0004: In-process queue with scale-out path

- Status: Accepted
- Decision: Use per-conversation in-process ordering initially.
- Rationale: It is sufficient for the first deployment and preserves a clear
  queue boundary. A durable queue and workers can replace it when multiple
  instances require shared ordering.
