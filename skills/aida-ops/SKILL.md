---
name: aida-ops
description: Modular Aida workflow bookkeeping and audit tooling.
memory_tags:
  - domain:aida
  - workflow:bookkeeping-audit
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - risk:medium
---

# Aida Ops

## Trigger

Use this skill for reusable Aida task bookkeeping and audit operations.

## Boundaries

- Specification/workflow source: `liferepo`/workspace Aida docs
- Private state source: `<private-repo>/openclaw/workspace/`

## Current Script Surface

Implementations currently live in:
- `skills/aida-ops/scripts/`

Legacy entrypoint remains at `<private-repo>/scripts/aida-bookkeeping-audit.mjs` as
a wrapper that delegates to this skill.
