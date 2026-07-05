---
name: public-website-foundation-ops
description: Use when starting or hardening a public website, catalog, radar, directory, companion page, product site, or installable-skill site so the repo has the required README, design contract, agent startup rules, environment contract, intake/lead-capture plan, verification commands, and launch boundary before implementation drifts.
memory_tags:
  - domain:frontend
  - workflow:public-website-foundation
  - skill_role:orchestrator
  - repo_boundary:tools
  - inputs:website-repo
  - outputs:launch-contract
  - risk:medium
---

# Public Website Foundation Ops

Use this skill before or during the first real build of a public website. The
goal is to make the boring launch contracts happen by default, not as a cleanup
pass after the site already exists.

## Trigger

Use when:
- starting a new public website, catalog, radar, directory, product site,
  profile page, link page, or installable-skill site
- turning a prototype into a public repo or deployed site
- adding a public request form, install command, lead gate, or generated data
  sync to a site
- a repo has app code but lacks a README contract, design contract, local
  verification commands, or public/private boundary

Do not use when:
- the task is only a private internal tool with no public surface
- the user only wants a narrow UI bug fix and the repo already has these
  contracts
- the work is only GitHub metadata or README cleanup; use
  `repo-readme-onboarding-ops`

## Required Contracts

Every public website repo should define these before it is considered ready:

- `README.md`: identity, live URL or intended URL, what visitors get, quick
  start, local development, environment variables, data/source model, primary
  workflow, verification commands, and support/intake route.
- `DESIGN.md` or equivalent: selected design mode, audience, layout density,
  typography/color/token choices, visual boundaries, and mobile/responsive
  expectations.
- `AGENTS.md` when repo-local rules matter: startup files to read, generated
  files not to hand-edit, public/private boundaries, and validation commands.
- `.env.example`: only server-safe variable names and clear comments. Never
  expose write tokens through `NEXT_PUBLIC_*`.
- Verification scripts: typecheck, build, UI/e2e test when applicable, and any
  generated-data validation command.
- Public/private boundary: source repos, generated files, sanitized export
  rules, and explicit non-goals.
- Intake path when users can submit requests: shared public/private issue
  queues, source labels, and server-side issue creation.
- Lead capture path when install commands are gated: server-side lead storage
  and no browser-exposed service keys.

## Skill Sequence

Use the smallest set that applies:

1. `website-page-planning-ops` for page structure, primary workflows, and CTA
   map.
2. `frontend-art-direction-ops` for visual direction or local `DESIGN.md`.
3. `frontend-catalog-design-ops` when the site is a searchable catalog, radar,
   directory, feed, or contribution-backed resource hub.
4. `installable-skill-lead-gate-ops` when a skill install command or setup
   command is visible to visitors.
5. `website-github-issue-form-ops` when the site accepts requests,
   suggestions, corrections, contributions, or private notes.
6. `repo-readme-onboarding-ops` before handoff so the README matches the built
   site and repo scripts.
7. `frontend-polish-pass-ops` before final delivery for responsive, visual,
   accessibility, and interaction checks.

Do not merge all details into this skill. This skill owns sequencing and the
minimum launch contract; focused skills own implementation details.

## Split From Private Launch Ops

This reusable skill should run before George-specific launch work. It answers:
"Does this public website repo have the contracts it should have from day
one?"

George-specific deployment and ownership details belong in a private overlay
such as `website-launch-ops`, including:

- Snack Overflow George domain conventions
- Vercel project/domain setup
- GitHub owner, repo visibility, and push/deploy steps
- shared private defaults for request intake targets
- private launch checklist decisions

Recommended sequence for George sites:

1. Run `public-website-foundation-ops` to establish the repo contract.
2. Use focused reusable skills for page planning, design, forms, lead gates,
   README, and polish.
3. Run the private website launch overlay for domains, Vercel, repo
   visibility, and final publication.

## Workflow

1. Classify the site:
   - catalog/radar/directory
   - product or launch site
   - personal/editorial/profile surface
   - companion page or learning artifact
   - internal/private tool
2. Inspect existing repo surfaces:
   - `README.md`
   - `AGENTS.md`
   - `DESIGN.md`
   - `.env.example`
   - `package.json`
   - `app/`, `pages/`, `src/`, `lib/`, `data/`, `feeds/`, `scripts/`,
     `tests/`
3. Write or update the launch contract before broad UI work:
   - first-screen product promise
   - design mode and constraints
   - source/data ownership
   - generated files and sync/validate commands
   - public/private intake behavior
   - verification checklist
4. Implement site behavior only after the contract is clear enough to check.
5. Before handoff, run the documented verification commands or explain exactly
   which command was unavailable.

## README Contract

Use this section order unless the repo already has a stronger local convention:

1. Project name and one-line outcome.
2. Live site or intended deployment URL.
3. What visitors get.
4. Quick start or install/setup path.
5. Local development.
6. Source/data model and generated-file rules.
7. Main user flow to try.
8. Verification commands.
9. Environment variables and server-only token rules.
10. Request/intake/contribution path.

For a public catalog or radar site, include the source repo, sync command,
validate command, generated data path, feed path, and warning not to edit
generated data by hand.

## Design Contract

Create or update `DESIGN.md` when a site does not already have a clear design
source. It should specify:

- audience and first-screen job
- selected design mode or visual reference
- density and navigation rules
- typography, color, spacing, and component constraints
- visual assets required
- responsive behavior and mobile risks
- what not to do

Prefer linking to an existing design-language repo or mode when available, then
record only the local adaptations in the target repo.

## Verification

A complete pass usually proves:

```sh
npm run typecheck
npm run build
npm run test:ui
```

When generated data exists, run the check-only validation before sync if the
repo supports it:

```sh
npm run validate:<domain>
npm run sync:<domain>
```

For static pages without a test harness, use the smallest available build or
preview command and inspect the rendered page.

## Boundaries

- Keep reusable website launch rules here.
- Keep private defaults, domain ownership details, credentials, and personal
  deployment notes in a private overlay or target repo.
- Do not add public forms that write to GitHub or a database without
  server-side token handling.
- Do not treat a pretty first screen as complete unless README, design,
  environment, intake, and verification contracts are also current.
