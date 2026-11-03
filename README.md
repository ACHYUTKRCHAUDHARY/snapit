# Snappe.ai

The Universal WhatsApp Replier: one reusable auto-replier engine for small
businesses, configured by a validated business profile.

## Development

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run lint-imports
```

The Phase 0 walking skeleton exposes `/healthz`, `/readyz`, and `/metrics`.
Product functionality is added incrementally in the later phases.
