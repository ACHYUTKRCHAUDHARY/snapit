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
- Added Rate Limiting and Outbound Resilience layer (Phase 3E):
  - Created `TokenBucket` and per-business `RateLimiter` returning HTTP 429 upon quota exhaustion.
  - Added 3-state `CircuitBreaker` (CLOSED, OPEN, HALF-OPEN) to `MetaWhatsAppSender` to protect against cascading Meta API failures.
  - Enhanced `RetryPolicy` with exponential `backoff_factor`.
  - Added idempotent event handling in `SQLConversationRepository.record_message`.
  - 109 tests passed, 94.71% coverage, 0 vulnerabilities, 0 bandit issues.
- Added Data Protection, Privacy & Retention Purge layer (Phase 3F):
  - Added `hash_phone` (salted SHA-256 for PII phone anonymization) and enhanced `mask_phone`.
  - Added SQL persistence methods `purge_before` (for time-based retention) and `purge_customer_data` (for GDPR/DPDP right-to-erasure).
  - Added `POST /privacy/retention/purge` and `POST /privacy/customers/{business_id}/purge` endpoints.
  - Attached `privacy_router` to `create_full_app`.
  - 112 tests passed, 94.94% coverage, 0 vulnerabilities, 0 bandit issues.
- Added Multi-Tenant Supabase Auth & JWT RS256 layer (Phase 3G):
  - Supported asymmetric public key signature verification (`RS256`) via `SUPABASE_JWT_PUBLIC_KEY` in addition to symmetric `HS256`.
  - Added multi-tenant metadata parsing (`business_id`, `email`, `app_metadata`).
  - Added `require_role` dependency factory for role-based route access controls (RBAC).
  - 115 tests passed, 95.06% coverage, 0 vulnerabilities (`cryptography>=46.0.6`), 0 bandit issues.
- Added Production Containerization & Deployment layer (Phase 3H):
  - Created multi-stage `Dockerfile` using `ghcr.io/astral-sh/uv` builder and non-root unprivileged runner (`snappe:snappe`) with built-in `/healthz` healthcheck.
  - Created `.dockerignore` excluding caches, tests, and temporary virtualenvs.
  - Created `docker-compose.yml` linking the API service with PostgreSQL 16, auto-mounting initial tenant schema migrations, and configuring service healthchecks.
  - Updated GitHub Actions CI workflow with Docker build validation and buildx cache.
