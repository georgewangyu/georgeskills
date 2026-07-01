---
name: live-proof-gate-ops
description: Define and enforce proof-before-done gates for agent workflows, automations, integrations, UI changes, and queued work.
memory_tags:
  - domain:agent-systems
  - workflow:live-proof-gate
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:workflow
  - outputs:verification-plan
  - risk:medium
---

# Live Proof Gate Ops

## Trigger

Use when:
- a task, automation, integration, or queue item needs a clear "done" verifier
- the user mentions proof gates, end-to-end testing, live verification, receipts, acceptance criteria, or "did it really work?"
- an agent workflow could pass mocks/tests while failing at the real external boundary
- a later-queue item is being promoted into active execution and needs a proof plan

Do not use when:
- the work is pure note-taking with no runtime, external, or user-facing boundary
- the user explicitly wants brainstorming only
- live testing would be unsafe, destructive, unauthorized, or privacy-invasive

## Inputs

- Required: task or workflow objective, changed surface, expected user-visible or system-visible outcome
- Optional: repo docs, test commands, credentials/access status, environment constraints, screenshots, logs, prior failures, release/merge target

## Workflow

1. Identify the real boundary:
   - file artifact, CLI command, web UI, mobile app, API/provider, email/social send path, scheduled automation, hardware/device, or human approval loop
2. Define the minimum acceptable proof:
   - command/test output for local code
   - browser or screenshot proof for UI
   - authenticated call/readback for external APIs
   - sent/received/readback evidence for messaging or email
   - generated artifact path plus validation for documents/media
   - automation run result plus schedule/config readback for recurring jobs
3. Separate proof levels:
   - `unit`: small deterministic test
   - `integration`: adjacent systems together
   - `live`: real account/provider/device/user path
   - `receipt`: concise evidence recorded in a queue item, PR, journal, or handoff
4. Decide the gate state:
   - `pass`: proof ran against the final candidate and matches the objective
   - `blocked`: exact access, credential, account state, device, or approval is missing
   - `waived`: owner explicitly accepts missing live proof for this item
   - `not-applicable`: pure docs/metadata/no live boundary; explain why
5. Record the result:
   - what was tested
   - command/path/account boundary used, without secrets
   - observed behavior
   - artifact or link
   - residual risk
   - next action if blocked

## Outputs

Return:
- proof boundary
- required proof level
- gate state
- evidence/receipt
- missing access or exact owner question
- residual risk
- recommended next action

For queue items, add or update a `proof` field. For PRs or commits, include proof in the final report or landing comment.

## Boundaries

- Do not fabricate live proof from confidence, mocks, docs, fixtures, or screenshots of unrelated states.
- Do not expose secrets, private data, internal identifiers, or credential values in receipts.
- Do not perform public, financial, account-mutating, or destructive actions unless the user explicitly approved that exact action.
- If live proof is blocked, finish safe prep work and ask for the exact missing access, waiver, or decision.
