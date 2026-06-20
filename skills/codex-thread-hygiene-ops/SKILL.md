---
name: codex-thread-hygiene-ops
description: Organize Codex conversations by reviewing pinned or recent threads, improving vague thread titles, and proposing pin/archive cleanup. Use when the user asks to rename chats, organize pinned chats, clean up previous Codex sessions, run thread hygiene, or prepare a manual review before creating a recurring automation.
memory_tags:
  - domain:workflow
  - workflow:thread-hygiene
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
6. Report concise results.
   - Include renamed threads with old title, new title, and reason.
   - Include skipped good titles as a count, not a long list.
   - Include proposed pin/archive changes separately from actions taken.

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
- skipped count for already-good titles
- review-needed candidates with short reasons
- recommended next automation scope, if the user is evaluating automation

## Boundaries

- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, private URLs, or local filesystem paths.
- Do not create a recurring automation from this skill unless the user separately asks for one.
- Prefer conservative title preservation over repeated renaming.
- Use Codex thread-management tools when available; if they are unavailable, explain the limitation and provide a manual review plan.
