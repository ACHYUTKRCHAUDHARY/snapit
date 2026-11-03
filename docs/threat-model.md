# Initial threat model

This is the Phase 0 threat baseline. It is not a substitute for a deployment
review.

| Asset | Threat | Initial control | Later verification |
|---|---|---|---|
| Customer messages | Prompt injection or unsafe instructions | Treat inbound text as data; strict brain schema and code guardrails | Phase 2 adversarial tests |
| Webhook endpoint | Forged/replayed requests | Meta signature verification and event deduplication | Phase 3 contract tests |
| Customer records | Excess collection or unauthorized access | Minimize fields, retention purge, export/delete audit trail | Phase 5 data-protection review |
| Team handover | Unauthorized resume or command abuse | Allowlist team members, masked logs, audited commands | Phase 3 command tests |
| Approved facts | Hallucinated prices/policies | Profile-backed fact checks and safe handover | Phase 2 guardrail tests |
| Secrets | Credential leakage | Environment-based configuration; never log secrets | Release secret scan |
| Availability | LLM/provider or action outage | Timeouts, retries, safe response, handover | Phases 2 and 4 chaos tests |

Security-sensitive events must be structured and auditable without storing
unnecessary message content or full phone numbers.
