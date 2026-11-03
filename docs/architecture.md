# Snappe.ai architecture

Snappe.ai is a reusable auto-replier. A new client supplies a validated profile;
business behavior is not implemented as client-specific code.

## Layers

```mermaid
flowchart LR
    C[Channel\nWhatsApp webhook] --> O[Application orchestration]
    O --> B[Brain\nLLM behind port]
    O --> P[Profile\nvalidated and hot reloadable]
    O --> A[Actions\nbooking, leads, orders, handover]
    A --> C
    O --> D[(Persistence)]
```

The channel verifies and normalizes inbound data. The application layer owns
ordering, deduplication, state transitions, guardrails, and audit decisions.
The brain proposes a strictly validated response; code-enforced guardrails
decide whether it may be sent. Actions are ports with replaceable adapters.

## Runtime flow

```mermaid
sequenceDiagram
    participant W as WhatsApp
    participant C as Channel
    participant O as Orchestrator
    participant P as Profile repository
    participant B as Brain
    participant G as Guardrails
    participant A as Action
    participant T as Team

    W->>C: webhook message
    C->>C: verify signature and deduplicate
    C->>O: normalized inbound message
    O->>P: resolve profile by phone_number_id
    O->>O: check conversation state and emergency keywords
    O->>B: profile + bounded history + customer data
    B-->>O: validated JSON proposal
    O->>G: enforce facts, safety, escalation, length
    G-->>O: allow or safe handover
    O->>A: route intent
    A-->>W: reply or handover response
    A-->>T: notify team when required
    O->>O: write message, decision, action, and audit records
```

## Boundaries

`snappe.domain` contains business concepts and rules. `snappe.application`
contains use cases and Protocol ports. `snappe.adapters` contains FastAPI,
WhatsApp, LLM, persistence, calendar, and scheduler implementations. Dependency
direction points inward; import-linter contracts enforce this boundary.

## Deployment

Phase 0 targets Render with a single FastAPI process and SQLite for local and
early deployment. The persistence port keeps a Postgres path open for scale.
The initial queue is in-process; a durable broker and worker pool can replace it
without changing domain use cases.
