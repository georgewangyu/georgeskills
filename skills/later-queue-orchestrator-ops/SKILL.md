---
name: later-queue-orchestrator-ops
description: "Orchestrate later/backlog queues: refresh items, classify routing, prepare decision-ready briefs, promote work, and enforce proof gates."
memory_tags:
  - domain:workflow
  - workflow:queue-orchestration
  - repo_boundary:tools
  - inputs:queue
  - outputs:queue-brief
  - risk:medium
---

# Later Queue Orchestrator Ops

## Trigger

Use when:
- the user wants a maintainer-orchestrator-style workflow for a later queue, backlog, someday list, or personal operating queue
- the queue needs more than formatting: prioritization, owner questions, promotion, deferral, or proof-gated closeout
- the user asks what to do next from a queue
- a daily, weekly, or sprint review needs a decision-ready queue brief

Do not use when:
- the user only wants to rewrite item formatting; use `later-queue-triage-ops`
- the user only needs a verifier for one task; use `live-proof-gate-ops`
- the queue contains high-stakes legal, tax, medical, or financial decisions; prepare questions and stop before advice or implementation

## Inputs

- Required: queue source and review horizon
- Optional: daily summaries, project docs, source artifacts, calendar constraints, owner preferences, existing proof receipts, max active items

## Workflow

1. Refresh the queue:
   - read the queue source and directly referenced source artifacts when needed
   - preserve existing ids, sources, statuses, and private context boundaries
   - run `later-queue-triage-ops` first if items are not already decision cards
2. Classify every relevant item:
   - `autonomous`: can be prepared or executed safely with current permissions
   - `needs-owner`: requires taste, priority, budget, access, approval, or external relationship judgment
   - `waiting`: blocked on another person, account, credential, event, or mounted resource
   - `defer`: real but should not surface before its review date
   - `kill-candidate`: stale, duplicate, superseded, or no longer worth carrying; ask before marking dead
3. Choose the review set:
   - surface at most three items by default
   - prefer due items, high-risk obligations, soon-expiring opportunities, and items with clear next actions
   - avoid promoting broad research when a concrete obligation is due
4. Prepare decision-ready briefs before asking the owner:
   - source
   - plain-language change or work
   - why the decision is needed now
   - completed proof or missing proof
   - risk and tradeoffs
   - recommendation
   - exact choices and consequences
5. Promote or execute only within permission:
   - queue review alone does not authorize file edits, public actions, purchases, account changes, commits, or destructive cleanup
   - if implementation is authorized, define the live-proof gate before starting
   - if approval/access is missing, stop with the exact owner question
6. Close out:
   - update item status only when the outcome is real
   - record proof receipts for completed items
   - move superseded detail to archive/done/dead instead of deleting history
   - seed the next review date or next action

## Outputs

Return:
- review horizon and queue scope
- active shortlist
- autonomous candidates
- owner decisions needed
- waiting/blocker list
- kill/defer candidates
- recommended next action
- proof gates or missing proof for promoted items

For each owner decision, include exact choices. Do not ask vague questions like "what should we do with this?"

## Boundaries

- This is a control-plane skill. Keep the queue review lightweight; move substantial execution into a focused task/thread.
- Do not convert queue review into open-ended research.
- Do not mark items done without proof or an explicit owner waiver.
- Do not delete queue history silently.
- Keep reusable skill text public-safe: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
