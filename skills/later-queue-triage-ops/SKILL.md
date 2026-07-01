---
name: later-queue-triage-ops
description: Convert later/backlog queues into source-first decision cards with fit, risk, proof, blockers, next action, and review routing.
memory_tags:
  - domain:workflow
  - workflow:queue-triage
  - skill_role:orchestrator
  - repo_boundary:tools
  - inputs:queue
  - outputs:decision-cards
  - risk:low
---

# Later Queue Triage Ops

## Trigger

Use when:
- the user wants to organize a later queue, backlog, someday list, or deferred work queue
- queue items are vague, stale, duplicated, or hard to choose from
- the user wants a maintainer-orchestrator-style pass without GitHub issue/PR assumptions
- a daily, weekly, or sprint review needs to promote, defer, kill, or clarify queued work

Do not use when:
- the user wants immediate execution of one already-clear task
- the queue source is unavailable and cannot be reconstructed from local context
- the task is legal, tax, medical, or financial decision-making rather than queue shaping

## Inputs

- Required: queue file, task list, notes section, or backlog source
- Optional: daily summary context, project docs, source links, due dates, owner constraints, review horizon, max surfaced items

## Workflow

1. Preserve queue identity:
   - keep existing item ids when present
   - keep original source references
   - do not silently delete items
2. Normalize each item into a source-first decision card:
   - `source`: URL, local path, email/note reference, transcript, or explicit "unknown"
   - `status`: later, scheduled, waiting, active, done, or dead
   - `captured` and `review_after`
   - `domain`, `effort`, `trigger`, and optional `due`
   - `what`: plain-language statement of the work
   - `why`: why it matters now or later
   - `fit`: good, mixed, or poor, with one reason
   - `risk`: low, medium, or high, with blast radius
   - `proof`: concrete verifier or missing-proof statement
   - `blocker`: first unresolved dependency, decision, access need, or "none"
   - `next`: smallest useful next action
3. Classify review routing:
   - `autonomous`: agent can prepare or execute within current permissions
   - `needs-owner`: decision, taste call, access, budget, account, or approval needed
   - `waiting`: blocked on another person, event, or external state
   - `defer`: real but not worth surfacing before its review date
   - `kill-candidate`: likely stale, duplicate, or superseded; requires explicit confirmation before marking dead
4. Reduce queue pressure:
   - surface at most three active candidates unless the user asks for a full sweep
   - split broad items only when the split creates clearer next actions
   - merge duplicates only with visible source preservation
5. For promoted work, require a proof plan before execution:
   - local command, file diff, live check, account/API proof, artifact path, or explicit waiver/access question

## Outputs

Return or write:
- rewritten queue cards
- review summary: active, waiting, defer, kill-candidate
- top three recommended next actions
- proof gaps and exact owner questions

When editing a queue file:
- preserve frontmatter and review ritual docs unless updating them is part of the request
- keep private paths and account details only in private repos
- avoid deleting history; use archive, done, or dead status instead

## Boundaries

- This skill organizes queued work; it does not authorize execution, commits, public actions, purchases, account changes, or irreversible cleanup.
- Treat financial, legal, medical, and tax items as prep/triage only; recommend professional review when decisions matter.
- Keep reusable skill text public-safe: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
