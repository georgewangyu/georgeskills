---
name: resend-ops
description: Set up or maintain Resend email integration, env wiring, and deployment-secret configuration.
memory_tags:
  - domain:email
  - workflow:resend-setup
  - skill_role:operator
  - repo_boundary:tools
  - risk:high
---

# Resend Ops

## Trigger

Use when:
- a repo needs Resend API or SMTP delivery wired
- the user asks where shared Resend credentials live across repos
- a deploy needs `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, or SMTP values backed by Resend

Do not use when:
- the task is inbox export or Gmail triage; use `email-ops`
- the task is general copywriting with no delivery or env wiring

## Inputs

- Required: target repo path and deployment target (`local`, `preview`, or `production`)
- Optional: sender email, recipient/testing address, whether the repo uses direct Resend API or SMTP

## Workflow

1. Load shared private credentials from:
   - `<private-repo>/.tokens/resend.env`
   Example:
   ```bash
   source "$LIFEREPO_PRIVATE_ROOT/.tokens/resend.env"
   ```
2. Inspect the target repo to determine delivery style:
   - direct API: expects `RESEND_API_KEY` and usually `RESEND_FROM_EMAIL`
   - SMTP: expects `SMTP_HOST=smtp.resend.com`, `SMTP_PORT=587`, `SMTP_USER=resend`, `SMTP_PASS=$RESEND_API_KEY`
3. Wire repo-local env files only inside the target repo for local development.
4. For deployed apps, add or update platform secrets rather than committing them to source control.
5. Verify that the sender domain is actually usable:
   - check the repo's configured `FROM_EMAIL` / `RESEND_FROM_EMAIL`
   - if delivery fails with sandbox restrictions, note that the verified sender/domain still needs work in Resend

## Output Contract

- which credential source was used
- whether the target repo uses direct Resend API or SMTP
- which local env files or deployment secrets were updated
- remaining blockers such as missing verified sender domain or recipient restrictions

## Guardrails

- Never commit `RESEND_API_KEY` into app repos or `georgeskills`.
- Treat `<private-repo>/.tokens/resend.env` as the shared local source of truth.
- If a live key was pasted into chat or logs, recommend rotating it after setup.
