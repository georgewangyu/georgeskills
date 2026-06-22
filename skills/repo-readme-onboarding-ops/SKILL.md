---
name: repo-readme-onboarding-ops
description: Audit and improve repository README files and GitHub About metadata so public projects have a clear first impression, quickstart path, usage proof, and contribution/onboarding surface.
memory_tags:
  - domain:documentation
  - workflow:repo-onboarding
  - repo_boundary:tools
  - inputs:repository
  - outputs:readme-audit
  - risk:medium
---

# Repo README Onboarding Ops

## Trigger

Use when:
- a user wants to improve one or many repository READMEs
- a repo's GitHub page feels generic, thin, stale, or hard to onboard into
- the task includes GitHub About metadata: description, homepage, topics, or social preview
- the user wants a README audit before editing many repos

Do not use when:
- the task is only agent steering docs; use repo `AGENTS.md`/`AGENT.md` conventions instead
- the user wants full API docs, changelog writing, or license selection as the primary task

## Core Lens

A README is the repo's front door and first user experience. It should make the
project legible before a visitor reads the code.

Use these source-backed principles:
- README-driven development: the README clarifies what the software is supposed
  to do and keeps scope small enough to explain.
- First viewport discipline: name, one-line outcome, visual or example output,
  and fastest useful action.
- Adoption path: installation, configuration, usage, and verification should be
  easy enough for a technical visitor to try without private context.
- Trust surface: GitHub description, homepage, topics, badges, screenshots,
  license, and contribution links should match the project's maturity.

## Inputs

- Required: repository path, GitHub repo, or GitHub owner/org.
- Optional: target audience, public/private boundary, whether to edit files or
  audit only, preferred output path, homepage/demo URLs, social-preview policy.

## Workflow

1. Establish scope.
   - One repo: inspect files directly.
   - Many repos: run `scripts/audit_github_readmes.py` first, then sample the
     highest-priority repos manually before recommending edits.
2. Inspect the repo's entry surfaces:
   - `README.md`
   - `AGENTS.md` / `AGENT.md`
   - package manifests and build files
   - docs/examples/screenshots
   - license/contributing/changelog files
   - GitHub About metadata when available
3. Classify the project type:
   - app/site
   - CLI/bot
   - library/toolkit
   - agent skill/prompt repo
   - personal/profile repo
   - private/internal repo
4. Score the README against the onboarding gates:
   - `identity`: what it is and who it is for
   - `proof`: screenshot, demo, GIF, example output, or real command
   - `quickstart`: fastest path to one useful result
   - `usage`: concrete examples beyond setup
   - `development`: local setup, test/build commands, and contribution path
   - `trust`: license, maintenance status, caveats, and support route
   - `metadata`: description, homepage, topics, and social preview
5. Recommend edits.
   - Keep README content human-facing.
   - Move agent-only operating rules to `AGENTS.md` or `AGENT.md`.
   - Link out to detailed API docs, license text, changelog, and long
     contribution docs instead of pasting them into the README.
   - Preserve true project-specific voice and remove generic template residue.
6. If editing is requested, patch the README in small repo-scoped batches.
   - Do not rewrite many repos in one giant mixed commit.
   - For public repos, avoid claims that are not supported by code, docs, or
     user-provided context.

## Batch Audit Command

```bash
python3 <georgeskills-root>/skills/repo-readme-onboarding-ops/scripts/audit_github_readmes.py \
  --owner <github-owner-or-org> \
  --out <private-output-path>/repo-readme-audit.md
```

Useful flags:
- `--limit <n>`: maximum repos to inspect
- `--public-only`: skip private repositories
- `--json-out <path>`: also write machine-readable audit JSON

## Output Contract

Return or create:
- ranked repo audit table
- per-repo gaps and concrete README edit recommendations
- proposed GitHub About description/homepage/topics
- pilot repo shortlist for first edits
- clear boundary between edits made and edits only recommended

## Boundaries

- Keep this skill reusable: no hardcoded personal handles, account IDs, private
  URLs, credentials, or local absolute paths.
- Treat private repository names and README content as user data; save audit
  outputs in the user's private repo when available.
- Do not publish, push, or edit GitHub About metadata without explicit user
  approval for that action.
