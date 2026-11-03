# ADR 0003: SQLite first, Postgres path

- Status: Accepted
- Decision: Start with SQLite and repository ports, while keeping schemas and
  transactions portable to Postgres.
- Rationale: SQLite minimizes operational overhead for the initial Render
  deployment; Postgres remains the scale-out persistence target.
