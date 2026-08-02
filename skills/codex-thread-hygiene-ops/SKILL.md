---
name: codex-thread-hygiene-ops
description: Review and update Codex thread titles, pins, and archive state, including verification when local and hosted thread records are ambiguous. Use for chat title hygiene, pinned/recent thread review, authorized pin cleanup, and pre-automation cleanup passes.
metadata:
  memory_tags:
    - domain:workflow
    - workflow:thread-hygiene
    - skill_role:operator
    - repo_boundary:tools
    - outputs:codex-thread-updates
    - risk:medium
---

# Codex Thread Hygiene Ops

## Trigger

Use when:
- the user asks to organize, rename, or review Codex chats
- pinned threads need clearer titles or stale-thread review
- recent threads have generic titles such as "New chat", "Question", "Debugging", or vague fragments
- the user wants a one-time hygiene pass before deciding on an automation

Do not use when:
- the user only asks to manage files, browser tabs, GitHub issues, Gmail threads, or non-Codex conversations
- the user asks to create a recurring automation but does not ask to inspect or rename threads first; use the automation tool directly

## Inputs

- Required: user scope, such as pinned threads, recent threads, a search query, or a specific thread id
- Optional: max thread count, rename-only mode, review-only mode, include archived threads, title style preferences

If the user gives no scope, default to a bounded manual pass over pinned and recent threads. Avoid broad historical backfills unless the user explicitly asks.

## Workflow

1. List candidate threads with the Codex thread tools.
   - Prefer pinned threads first when the user mentions pinned-chat cleanup.
   - Include recent unpinned threads only within the user's requested limit.
2. Read enough thread context to infer the durable task.
   - Prefer recent turn summaries first.
   - Read older turns only when the title decision is ambiguous.
   - Do not include raw tool outputs unless needed to distinguish similar tasks.
3. Classify the current title.
   - `good`: specific, stable, and recognizable on its own.
   - `acceptable`: not perfect, but clear enough to avoid churn.
   - `vague`: generic, auto-generated, too broad, or missing the project/task.
   - `stale`: was once accurate but no longer matches the main durable work.
4. Rename only when the improvement is clear.
   - Automatically rename `vague` titles when a better title is high-confidence.
   - Rename `stale` titles only when the latest durable direction clearly supersedes the old title.
   - Skip `good` and `acceptable` titles.
   - If uncertain, leave the title unchanged and include a recommendation in the summary.
5. Keep pin/archive changes review-first unless the user explicitly asks for direct action.
   - Propose stale pins, duplicate threads, or completed threads as cleanup candidates.
   - Do not unpin or archive during the first hygiene pass unless the user clearly authorizes it.
6. Apply authorized pin changes with the verified local-mutation protocol below.
7. Report concise results.
   - Include renamed threads with old title, new title, and reason.
   - Include skipped good titles as a count, not a long list.
   - Include proposed pin/archive changes separately from actions taken.

## Verified Local Pin Mutations

Treat a pin receipt as evidence for the record it names, not automatic proof
that the visible local sidebar changed. Codex may expose the same thread id
through both local and hosted catalogs.

For an authorized local-sidebar pin change:

1. Record the calling thread id so the app can return to it afterward.
2. Resolve the exact target id from the reviewed inventory; never mutate by
   title alone.
3. Navigate the main Codex window to that exact target with
   `navigate_to_codex_page`.
4. Call `set_thread_pinned` only after the target is focused.
5. Inspect the receipt. If it names an unexpected hosted or remote source,
   treat the requested local mutation as unverified even when `pinned: false`
   is returned.
6. For multiple targets, repeat focus then mutation one target at a time. Return
   the app to the recorded calling thread when finished.
7. Verify the actual local retained-pin set through a supported app inventory
   or a read-only local sidebar-state check. Do not infer pin state from list
   ordering when the inventory omits a pin field.
8. Report success only when the local state reflects the requested change. If
   verification fails, report the mutation as incomplete and preserve the
   user's remaining pins.

Do not dismiss a local mismatch as cache lag without evidence. Do not edit
Codex application state files directly as a shortcut.

## Title Rules

Prefer titles that fit this pattern:

`<Project or Domain>: <Concrete Task or Outcome>`

Examples:
- `Codex: Thread Title Hygiene Skill`
- `XBot: Timeline Check Workflow`
- `Resume: ATS Validation Cleanup`
- `Stripe: Webhook Setup Debugging`
- `Journal: Daily Summary Finalization`

Use short, durable nouns. Avoid titles that describe only the immediate action, such as "Fix bug", "Run command", or "Follow up", unless that is truly the whole thread.

## Re-Run Policy

Avoid wasting future runs on titles that are already useful:

- Treat `good` and `acceptable` titles as stable.
- Do not rename a stable title just because a slightly better phrasing is possible.
- Reconsider a stable title only when the thread's recent turns show a materially different durable task.
- If the conversation has temporarily branched but the original durable task still dominates, keep the existing title.
- When in doubt, preserve the current title and report the ambiguity.

## Output

Return:
- actions taken, grouped by title updates, pin updates, and archive updates
- pin-verification source and the exact retained set after mutations
- skipped count for already-good titles
- review-needed candidates with short reasons
- recommended next automation scope, if the user is evaluating automation

## Boundaries

- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, private URLs, or local filesystem paths.
- Do not create a recurring automation from this skill unless the user separately asks for one.
- Prefer conservative title preservation over repeated renaming.
- Use Codex thread-management tools when available; if they are unavailable, explain the limitation and provide a manual review plan.
