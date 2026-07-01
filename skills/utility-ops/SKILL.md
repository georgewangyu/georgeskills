---
name: utility-ops
description: Modular utility tooling for resume conversion, PDF text helpers, repository summary generation, and document frontmatter backfills.
memory_tags:
  - domain:utility
  - workflow:maintenance
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - risk:low
---

# Utility Ops

## Trigger

Use this skill for reusable utility scripts that are not domain-specific:
- document conversion helpers
- lightweight local extraction helpers
- repository metadata/summaries generation
- document frontmatter normalization/backfills

## Boundaries

- Specification source: `liferepo` docs where relevant
- Private state source: `<private-repo>`

## Current Script Surface

Implementations currently live in:
- `skills/utility-ops/scripts/`

Legacy entrypoints remain in `<private-repo>/scripts/utils/` as wrappers that
delegate to this skill.
