# ADR 0006: Authorized handover resume

- Status: Accepted
- Decision: An authorized team member may issue strict WhatsApp commands
  (`RESUME`, `CLOSE`, `LIST`, `HELP`) from an allowlisted profile number.
  Operators may use the CLI. Customers can never resume a handed-over chat.
- Rationale: This preserves the human pause guarantee while allowing practical
  operations without an admin API in v0.1.
- Details: Handover codes are short and unguessable, phone numbers are masked,
  commands bypass the LLM, and every handover/resume/close/rejected command is
  audited. Reminder delivery is one reminder at the configured interval and
  one at two hours; reminders never resume a bot. A future scale-out command
  service may replace the in-process command handler.
