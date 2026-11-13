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
- Added durable SQLAlchemy persistence layer (`snappe.adapters.models`):
  - Declarative models: `BusinessProfileModel`, `ConversationModel`, `MessageModel`.
  - Added `SQLProfileRepository` implementing `ProfileRepository` port with versioning and activation.
  - Added `SQLConversationRepository` and `ConversationRepository` port for conversation state and message audit logging.
  - Added `Database.create_tables()` for metadata initialization.
- Added operator command engine and lifecycle endpoints (Phase 3C):
  - Created `parse_operator_command` for slash commands (`/pause`, `/resume`, `/close`, `/status`).
  - Extended `HandoverManager` and `HandoverState` to support conversation lifecycle (`active`, `handover`, `closed`).
  - Added `POST /handover/{conversation_id}/close` and unified `POST /handover/command` endpoint.
  - Added comprehensive syntax and operator workflow tests (101 total tests passing).
- Wired durable SQL persistence into live webhook pipeline (Phase 3D):
  - Added `ConversationAuditor` port to `MessageOrchestrator` to automatically audit-log inbound customer messages, outbound AI replies, delivery outcomes, and handover transitions.
  - Injected `get_conversation_repository` in `interfaces.webhook` providing real relational persistence.
  - Added integration test ensuring full database audit trail for inbound customer queries and outbound bot replies.
