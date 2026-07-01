---
name: later-queue-orchestrator-ops
description: "Orchestrate later/backlog queues: review items, choose next actions, route owner questions, and enforce proof gates."
memory_tags:
  - domain:workflow
  - workflow:queue-orchestration
  - skill_role:orchestrator
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
   - exception: if a higher-level automation explicitly delegates unattended git commit/push routing to this skill, use the "Unattended git publication routing" criteria below; only `autonomous-push` items may be pushed without owner review
   - if implementation is authorized, define the live-proof gate before starting
   - if approval/access is missing, stop with the exact owner question
6. Close out:
   - update item status only when the outcome is real
   - record proof receipts for completed items
   - move superseded detail to archive/done/dead instead of deleting history
   - seed the next review date or next action

## Unattended git publication routing

Use this section only when an automation explicitly asks this skill to decide
whether local commits should be pushed without owner review.

Classify each repo/branch push candidate as one of:

- `autonomous-push`: push now, then report the receipt.
- `needs-owner`: surface for owner review before pushing.
- `waiting`: blocked on credentials, upstream config, network, or remote state.
- `defer`: not worth surfacing yet because there are no pushable local commits.

An item is `autonomous-push` only when all of these are true:

1. The branch has a configured upstream and the push is a normal fast-forward
   push of local commits to that upstream. No force push, tag push, release
   publish, protected-branch override, or remote retargeting.
2. The repo has no merge/rebase conflict, unresolved index state, submodule
   uncertainty, or unrelated dirty work that could be confused with the commits
   being published.
3. The candidate commits have been inspected at commit and file-summary level,
   and the touched paths are routine for that repo: docs, tests, source,
   config, generated reports, or other known project artifacts.
4. Public/private safety is clear. For public or public-facing repos, the
   commits contain no credentials, tokens, private keys, env files, private
   local paths, personal records, client/customer data, unpublished contracts,
   health/finance/legal records, or private repo material.
5. Secret/publication checks available in the repo pass. At minimum run the
   repo's configured pre-commit or public-safety check when present, plus a
   basic diff sanity check such as `git diff --check` before committing local
   changes.
6. Code or behavior changes have appropriate validation for the repo and blast
   radius. If tests/builds are unavailable or skipped, the reason is low-risk
   and explicit.
7. Binary, large, encrypted, or generated design artifacts are known-safe for
   that repo and expected in the commit. Otherwise route to `needs-owner`.
8. The commit message and diff do not reveal private context that would be
   inappropriate for the target remote.

Route to `needs-owner` when any criterion is uncertain, especially:

- secret scanner or public-safety warning
- unknown public/private status for the target remote
- private-personal, health, finance, legal, tax, credential, client, or
  relationship material
- `.env`, key, token, credential, database dump, browser profile, chat export,
  transcript, or raw capture files
- unexpected binary/large files, encrypted design files, or generated assets
  whose publication value is unclear
- branch divergence, missing upstream, failed validation, ambiguous staging, or
  commits that mix unrelated work

For unattended runs, surface only `needs-owner` and `waiting` items by default.
Do not ask the owner to approve `autonomous-push` items after the fact; report
what was pushed, which checks passed, and the remote/branch receipt.

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
