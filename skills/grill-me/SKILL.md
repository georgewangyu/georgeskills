---
name: grill-me
description: Run a rigorous, one-question-at-a-time software design interview before implementation. Use when the user says "grill me," wants to stress-test an API, service, feature, architecture, migration, or coding plan, or needs to turn a vague engineering task into an implementation-ready design with explicit scope, acceptance criteria, tests, failure handling, security, operability, rollout, and proof.
---

# Grill Me

Turn an underspecified software idea into a decision-complete design. Challenge the design without rewarding unnecessary complexity.

## Operating Contract

- Ask exactly one question per turn and wait for the answer.
- Include a recommended answer with every question, plus the decisive rationale or tradeoff.
- Follow dependencies: resolve the decision that changes the most downstream choices first.
- Inspect available code, repository instructions, schemas, documentation, and external facts instead of asking the user questions that tools can answer.
- Ask the user about intent, priorities, constraints, risk tolerance, and product tradeoffs that cannot be discovered.
- Stay in interview mode. Do not implement, edit, deploy, or send anything until the user explicitly ends the grilling phase and authorizes execution.
- Prefer the simplest design that satisfies the agreed requirements. Treat added components as liabilities until justified.

Use this response shape during the interview:

```markdown
Question <n> — <decision>

<one focused question>

Recommended answer: <specific recommendation>

Why: <decisive rationale and main tradeoff>
```

Do not hide several questions inside bullets or subclauses. If an answer exposes a dependency, ask about that dependency next.

## Build the Decision Path

Start by establishing the smallest useful context:

1. Define the user-visible outcome and primary actor.
2. Separate required scope, optional scope, and explicit non-goals.
3. Identify constraints: time, compatibility, scale, latency, cost, compliance, existing systems, and delivery boundary.
4. List the few unresolved decisions that could materially change the design.
5. Walk those decisions in dependency order rather than following a fixed checklist.

For an existing repository, load its instructions and inspect the relevant implementation before asking architecture questions. State any inferred constraint and let the user correct it.

## Grill the Software Design

Cover each applicable lens before declaring the design ready.

### Requirements and Boundaries

- Actors, use cases, success outcome, and non-goals
- Functional requirements and externally visible behavior
- Compatibility requirements and ownership boundaries
- Explicit assumptions and unanswered product decisions

### Architecture and State

- Component boundaries and responsibility of each component
- Request, event, and data flow
- Source of truth, state ownership, lifecycle, and retention
- Consistency, concurrency, ordering, idempotency, and transactional boundaries
- Dependency choices and why each new component is necessary

### Interfaces and Data Contracts

- API, event, CLI, or UI contract
- Input validation, response shape, errors, versioning, and compatibility
- Data model, identifiers, pagination, schema evolution, and invariants
- Authentication, authorization, tenant isolation, privacy, and secret handling

### Reliability and Scale

- Dependency failures, partial failures, retries, timeouts, cancellation, and recovery
- Duplicate, delayed, missing, malformed, and out-of-order work
- Capacity assumptions, bottlenecks, backpressure, rate limits, and cost controls
- Degraded behavior and what the user observes during failure

### Operability and Delivery

- Logs, metrics, traces, audit signals, alerts, and debugging hooks
- Configuration, environments, deployment, migration, and rollback
- Safe rollout, feature flags, compatibility window, and cleanup plan
- Support ownership and the evidence required to call the work done

Skip irrelevant lenses explicitly. Do not invent distributed-systems problems for a local script, but do not let a networked or multi-user system escape concurrency, failure, and security questions.

## Forge Acceptance Criteria

Convert settled decisions into acceptance criteria before discussing implementation details. Make every criterion:

- observable from a user or system boundary
- specific enough to pass or fail
- independent of incidental implementation details unless the implementation is itself required
- inclusive of the normal path, important edge cases, and failure behavior
- paired with a named verifier

Use `Given / When / Then` when it improves precision, but do not force the syntax when a concise invariant is clearer.

Reject criteria such as "works correctly," "handles errors," or "is scalable." Replace them with bounded behavior, for example:

```text
Given a tenant already has five running jobs,
when it submits another job,
then the service rejects the request with 429 and a retry hint without sending work downstream.
```

## Map Criteria to Tests and Proof

Require a verification map before declaring readiness:

| Acceptance criterion | Verification layer | Proof | Required test double or live boundary |
| --- | --- | --- | --- |
| `<criterion>` | unit / contract / integration / end-to-end / load / security / migration | `<assertion or observed outcome>` | `<boundary>` |

Apply the smallest sufficient mix:

- Unit tests for pure policy, validation, transformations, and state transitions
- Contract tests for API shapes and third-party adapter assumptions
- Integration tests for storage, queues, SDKs, and adjacent components
- End-to-end tests for the primary user journey and real assembly
- Concurrency or load tests for shared state, throttling, ordering, and capacity claims
- Security tests for ownership, authorization, isolation, and unsafe inputs
- Migration and rollback tests when persistent state or compatibility changes

Demand red-capable proof: a test must be able to fail when the behavior is wrong. A mock proving only that a mock returned its fixture is not evidence that an integration works.

## Challenge Weak Decisions

- Ask for the failure mode hidden by words such as "simple," "generic," "later," "scalable," or "secure."
- Distinguish a deliberate non-goal from forgotten work.
- Surface the cost of the recommended design and the strongest credible alternative.
- Record unresolved risks instead of smoothing them into confidence.
- Reopen an earlier decision when new information invalidates it.
- Summarize settled decisions after a long branch so the user can correct drift.

## Exit Gate

Do not declare the design implementation-ready while a critical product, data, security, failure-recovery, acceptance, or proof decision remains unresolved.

When the applicable lenses are covered, present a compact readiness summary containing:

1. Objective and actors
2. Scope and non-goals
3. Constraints and assumptions
4. Proposed architecture and data flow
5. State, API, and data contracts
6. Failure, security, scale, and operability decisions
7. Numbered acceptance criteria
8. Acceptance-criterion-to-test map
9. Rollout, migration, and rollback plan
10. Open risks and deferred decisions
11. Recommendation: `ready to implement` or `not ready`, with the reason

Ask the user to confirm or correct that frozen design. Continue grilling if they change a material decision. Implementation requires a separate explicit instruction.

## Attribution

The one-question-at-a-time interview pattern is inspired by Matt Pocock's MIT-licensed `grilling` skill; this workflow expands it into an independently written software-design, acceptance, and verification gate.
