# Georgeskills Improvements

## Skill Quality Checklist

**Captured**: 2026-07-04
**Status**: open
**Priority**: high

### User Problem

Skill quality currently depends on manual review. New skills can ship with
missing trigger clarity, weak output contracts, unclear boundaries, or no
memory tags.

### Product Principle

Reusable skills should be inspectable as small operating contracts: trigger,
inputs, workflow, outputs, guardrails, metadata, and verification.

### V1 Improvement

Add a root-level skill quality checklist that can be reused during PR review
and new-skill creation.

### Future Builds

- `scripts/validate_skills.py`: validate required sections and frontmatter.
- A README index that maps each skill to private-repo dependencies and expected
  outputs.
- Periodic stale-skill detection for skills that are not touched but still
  appear in active workflows.

### Acceptance Criteria

- New skills have `Trigger`, `Inputs`, `Workflow`, `Outputs`, and `Boundaries`
  or an explicit reason for a different shape.
- Every public skill has `memory_tags`.
- Reviewers can run one command to find missing required fields.
- Validation distinguishes hard failures from advisory cleanup.

## External CLI Compatibility Matrix

**Captured**: 2026-07-04
**Status**: open
**Priority**: medium

### User Problem

Some skills rely on external CLIs or platform tools. When a tool changes, a
skill can fail even though the instructions still look current.

### Product Principle

Skills that depend on external tools should state supported versions,
installation assumptions, and known breakpoints close to the workflow.

### V1 Improvement

Add a compatibility matrix for key external CLIs used by skills.

### Future Builds

- Version probes for recurring CLIs.
- Per-skill compatibility notes linked from the matrix.
- A periodic check that flags missing or stale version guidance.

### Acceptance Criteria

- High-use skills list their required external tools.
- The matrix states version ranges or tested versions where known.
- A reviewer can tell whether a failure is likely setup drift or skill logic.

## Public Website Foundation

**Captured**: 2026-07-04
**Status**: shipped
**Priority**: high

### User Problem

New public websites were often built before the README, design contract,
environment contract, intake path, and verification commands were all explicit.

### Product Principle

Public websites should start with their launch contract, not discover it after
the first working UI.

### V1 Improvement

Add `public-website-foundation-ops` as the orchestration skill for new public
sites, catalogs, radars, directories, and installable-skill websites.

### Acceptance Criteria

- The skill requires README, `DESIGN.md`, repo-local agent rules when needed,
  `.env.example`, generated-data rules, intake/lead-capture rules, and
  verification commands.
- The skill sequences existing focused skills instead of replacing them.
- New website work has a clear default place to start.
