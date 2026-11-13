# Snappe.ai

The Universal WhatsApp Replier: one reusable auto-replier engine for small
businesses, configured by a validated business profile.

## Development

```powershell
uv sync
uv run poe check
```

Individual checks are available with `uv run poe lint`, `uv run poe format`,
`uv run poe typecheck`, `uv run poe imports`, and `uv run poe test`.

The Phase 0 walking skeleton exposes `/healthz`, `/readyz`, and `/metrics`.
The first product slice adds versioned business profiles with approved facts.
Profiles remain inactive until explicitly approved; only the active profile is
eligible for customer-facing responses.

The remaining core phases are now represented by typed application primitives:

- Brain guardrails reject ungrounded, oversized, or handover-requesting replies.
- Channel events support constant-time signatures and replay deduplication.
- Handover remains paused until an authorized operator sends an exact resume
  command.
- Actions use bounded retries and expose outages explicitly.
- Data protection provides phone masking and retention-port enforcement.
