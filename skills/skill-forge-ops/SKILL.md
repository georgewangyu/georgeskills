---
name: skill-forge-ops
description: Mine journals, transcripts, pull requests, commit history, scripts, and agent session notes for repeated workflows that should become reusable skills; draft and validate public-safe skill specs after human approval.
memory_tags:
  - domain:workflow-systems
  - workflow:skill-forging
  - skill_role:orchestrator
  - repo_boundary:tools
  - risk:medium
---

# Skill Forge Ops

## Trigger

Use when:
- the user wants to find workflows worth turning into skills
- the user asks to scan journals, transcripts, PRs, commits, or chat/session notes for repeated agent workflows
- the user wants to draft, refine, or validate a new `georgeskills` skill from observed behavior
- the user asks for a weekly/monthly skill candidate digest

Do not use when:
- the user already named a specific existing skill that fully covers the task
- the workflow is clearly a one-off note, not a repeated operating procedure
- private data must be copied into a public skill; keep private examples in the private repo or summarize them generically

## Inputs

- Required: source scope, such as daily journals, transcripts, PRs, commits, scripts, or specific artifact paths.
- Optional: time window, target domain, candidate limit, whether to only discover candidates or also draft a selected skill.

## Modes

- `discover`: scan source artifacts and produce a ranked candidate digest.
- `draft`: turn one approved candidate into a reusable `SKILL.md` and optional scripts/references.
- `validate`: check a draft skill for trigger clarity, repo boundaries, public safety, and practical usefulness.

## Discover Workflow

1. Establish the source scope and whether the output should be saved in the private repo.
2. Prefer artifact-first evidence:
   - daily journals and conversation milestones
   - transcript processing notes and generated transcript paths
   - PR descriptions, review comments, commit messages, and CI-fix notes
   - recurring scripts or repeated shell commands
   - agent session notes where the same instructions are repeated
3. Run the bundled scanner when useful:
   - `python3 skills/skill-forge-ops/scripts/scan_skill_candidates.py --root <path> --output <private-repo>/notes-private/skill-forge/YYYY-MM-DD_candidates.md`
   - pass multiple `--root` values for multiple artifact trees
   - use `--since-days <n>` to limit by file modification time
4. Read the digest and apply judgment. Promote only workflows with:
   - repeated evidence from at least two artifacts or sessions
   - a crisp trigger phrase
   - a stable input/output contract
   - meaningful advantage over a normal chat answer
   - public-safe reusable instructions
5. Return a short ranked table:
   - candidate
   - evidence
   - why it deserves a skill
   - suggested skill name
   - expected inputs/outputs
   - risks or reasons to ignore

## Draft Workflow

1. Get explicit approval for the specific candidate to promote.
2. Read `AGENTS.md`, `README.md`, `MEMORY_TAGS.md`, and `templates/SKILL_TEMPLATE.md`.
3. Create `skills/<skill-name>/SKILL.md` with:
   - clear YAML `name`, `description`, and `memory_tags`
   - trigger and do-not-use conditions
   - required and optional inputs
   - concrete workflow steps
   - output contract
   - repo and privacy boundaries
4. Add scripts only when they remove repeated mechanical work or improve reliability.
5. Keep detailed private examples out of the public skill. Use placeholders or generic descriptions.
6. Update the skill catalog in `README.md`.

## Validate Workflow

1. Run repository safety checks before commit:
   - `python3 .githooks/public-safety-check.py`
2. Check that the skill is not just a renamed chat prompt:
   - the trigger is specific
   - the workflow has durable steps
   - the output is testable
   - private paths, names, handles, credentials, and account defaults are absent
3. Test the skill against one realistic prompt or artifact sample.
4. If the draft is weak, leave it as a private candidate note instead of adding a public skill.

## Outputs

- Discovery mode: a ranked Markdown candidate digest, usually saved under `<private-repo>/notes-private/skill-forge/`.
- Draft mode: a new or updated `skills/<skill-name>/SKILL.md`, optional scripts/references, and README catalog update.
- Validate mode: a concise pass/fail note with issues to fix before promotion.

## Boundaries

- Public specs live in `liferepo`.
- Private source artifacts and candidate digests live in `<private-repo>`.
- This skill only owns reusable skill-discovery, drafting, and validation behavior.
- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, private URLs, or user-specific defaults.
