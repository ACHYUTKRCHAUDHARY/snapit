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
Product functionality is added incrementally in the later phases.
