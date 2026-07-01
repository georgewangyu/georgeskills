---
name: installable-skill-lead-gate-ops
description: >-
  Add or retrofit a Books/Loops Radar-style email unlock before showing an
  installable agent skill command on a website. Use when a public site,
  catalog, radar, directory, or resource hub distributes an installable skill
  and needs name/email lead capture, Supabase radar_leads storage, a repo-star
  CTA, Vercel env wiring, docs, and frontend tests.
memory_tags:
  - domain:skills
  - workflow:lead-gate-installation
  - skill_role:operator
  - repo_boundary:tools
  - inputs:skill-repo
  - outputs:lead-gate
  - risk:medium
---

# Installable Skill Lead Gate Ops

## Overview

Use this skill to make an installable-skill website collect a lightweight lead
before revealing the install command. The default pattern is name + email on
the front page, a server-side Supabase upsert, then an unlocked install command
with copy and "star the repo" actions.

Use `references/books-loops-pattern.md` as the implementation reference when
you need UI copy, state names, schema shape, API behavior, test cases, and
deployment checks.

## Trigger

Use this skill when the user asks to:

- Add an email unlock, lead magnet, waitlist, or install gate to a public
  website that distributes an installable agent skill.
- Reuse the Books Radar / Loops Radar website pattern on a new radar, catalog,
  directory, resource hub, or skill page.
- Save website leads in Supabase, wire Vercel env vars, and reveal the install
  command only after name/email submission.
- Add a repo-star prompt after the install command is unlocked or after first
  useful skill activation.

Do not use this skill for full newsletter automation, payment gates, private
account onboarding, or in-app authentication unless the user explicitly asks to
extend the pattern.

## Required Inputs

Resolve these from the repo when possible:

- Product name and product slug.
- Install command to reveal.
- Repository URL for the "star the repo" CTA.
- Website framework and deployment target.
- Existing Supabase project/env setup, or user approval to create/select one.

If any of these are missing, infer conservative placeholders from the repo and
call out assumptions in the final response.

## Workflow

1. Read local instructions first: nearest `AGENTS.md`, README, existing env
   examples, and the current front page or install section.
2. Identify the existing install command, repo URL, product slug, and where the
   command is currently exposed.
3. Prepare storage:
   - Prefer an existing configured Supabase project.
   - Create or select a dedicated project only when the user has explicitly
     approved that direction.
   - Use one shared `radar_leads` table across products, keyed by
     `(product, email)`.
   - Keep the service role key server-side only. Never expose it to browser
     code, public docs, logs, or screenshots.
4. Add the server API:
   - Validate `name` and `email`.
   - Include a hidden honeypot field to reduce simple bot submissions.
   - Upsert into `radar_leads` with `source = "website-install-gate"`,
     `consent_updates = true`, and `install_command_revealed = true`.
   - Capture product, repo URL, referrer, user agent, and timestamps.
5. Replace the visible install command with the unlock experience:
   - Ask only for name and email by default.
   - After successful submission, reveal the install command, copy action, and
     repo-star CTA.
   - Persist the unlocked state in product-scoped local storage so returning
     visitors do not need to resubmit.
6. Match the Books/Loops Radar interaction pattern:
   - Keep the unlock block on the front page near the installable-skill pitch.
   - Use a compact two-column layout on desktop and a stacked layout on mobile.
   - Keep copy direct: valuable outcome first, form second, command third.
   - Avoid extra fields unless the user asks for them.
7. Update skill onboarding when the repo contains an installable skill:
   - After the first useful activation, ask the user to star the repo if they
     want to save and support the project.
   - Keep this ask optional and low-friction.
8. Update docs:
   - `.env.example` or equivalent for `SUPABASE_URL` and
     `SUPABASE_SERVICE_ROLE_KEY`.
   - README setup notes for the lead table and deployment env vars.
   - Any contribution or launch docs that still mention an ungated command.
9. Verify:
   - Run the repo's typecheck, build, and relevant UI tests.
   - Add or update tests for successful unlock, validation errors, copy action,
     star link, and mobile layout where a frontend test suite exists.
   - Smoke-test the deployed API only when credentials and preview protection
     allow it. Clean up test rows afterward.
10. Deploy when requested:
    - Set Vercel Preview and Production env vars.
    - Redeploy after env changes; existing deployments do not automatically
      inherit new env values.
    - If the preview is protected by SSO, report that external smoke tests may
      redirect before reaching the app.

## Output Contract

When finished, report:

- Files changed and the behavior added.
- Supabase table/project status without revealing secrets.
- Deployment URLs or local test URLs, if applicable.
- Validation commands run and whether they passed.
- Any smoke-test limits, cleanup performed, or production redeploys still
  needed.
