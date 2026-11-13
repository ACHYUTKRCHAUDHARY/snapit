# Changelog

## Unreleased

- Added the Phase 0 quality gates, dependency checks, and architecture import
  contracts.
- Added versioned business profiles with approved-facts validation and explicit
  activation.
- Added the remaining phase primitives for brain guardrails, webhook
  verification, handover authorization, bounded action retries, and data
  retention/masking.
- Added external HTTP interfaces for profiles, WhatsApp webhook verification
  and event ingestion, and operator handover management.
- Added LLM brain service with injection-resistant prompt construction
  (`<customer_message>` XML delimiters), structured JSON output parsing, and
  safe handover fallback on outage or guardrail violations.
- Added Gemini API adapter (`GeminiLLMClient`) and deterministic
  `FakeLLMClient` for hermetic test isolation.
- Added adversarial guardrail tests covering prompt injection, hallucination,
  oversized replies, and customer-side `/resume` bypass attempts.
- Added WhatsApp Cloud API outbound adapter (`MetaWhatsAppSender`) with real
  Meta Graph API integration, `FakeWhatsAppSender` for hermetic tests, and
  delivery status tracking (`ResponseResult.delivered`).
- Wired outbound sender into `MessageOrchestrator`; delivery failures surface
  as `delivered=False` without triggering a second handover.
- Added `META_PHONE_NUMBER_ID` and `META_ACCESS_TOKEN` settings fields.
