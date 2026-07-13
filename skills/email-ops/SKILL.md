---
name: email-ops
description: Work with the private Gmail pipeline for export, triage context, scope verification, and lightweight send or reply helpers.
memory_tags:
  - domain:email
  - workflow:email-export
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - inputs:email
  - outputs:markdown-export
  - risk:high
---

# Email Ops

## Trigger

Use when:
- the user wants email export or inbox context
- the task is email triage, reply drafting support, or Gmail scope verification
- the workflow needs fresh email artifacts under `<private-repo>/captures/email/`

Do not use when:
- the task is broad multi-source export prep across email, calendar, and notes; use `exports-ops`
- the task is general writing with no inbox interaction

## Workflow

1. Use the stable private wrappers:
   - `python3 scripts/exports/email/export_emails_gmail_api.py`
   - `python3 scripts/exports/email/verify_gmail_scopes.py`
2. When the task explicitly needs send/reply support, use:
   - `python3 scripts/exports/email/send_email_gmail_api.py`
3. Prefer these wrappers over connector-provided Gmail tools for routine email work. Treat connector tools as a read-oriented fallback for bounded search or retrieval when the private export path is unavailable or stale.
4. Do not use connector-provided Gmail draft or send actions by default. For outbound work, draft the copy for review first, then use the account-verified private helper only after the user approves the exact message and asks to send it.
5. Read the exported markdown under:
   - `captures/email/`
6. Summarize actionable threads, waiting-on-reply threads, and admin noise separately.

## Output Contract

- what command ran
- whether auth/scopes look healthy
- where exports landed
- notable reply-needed threads or blockers

## Guardrails

- Treat all email exports as private derived data.
- Do not hardcode mailbox identities or credentials in the skill.
- Do not rely on connector send/draft actions unless the user explicitly asks for that surface and the authenticated account has been verified.
- Separate "reply needed" from "already answered" so triage stays useful.
