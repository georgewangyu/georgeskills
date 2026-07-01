---
name: memory-ops
description: Modular tooling for structured memory extraction, validation, promotion workflows, and document access/salience indexing.
memory_tags:
  - domain:memory
  - workflow:candidate-promotion
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - risk:medium
---

# Memory Ops

## Trigger

Use this skill when building reusable tooling for:
- extracting memory candidates
- validating record shape
- promoting reviewed candidates

## Boundaries

- Specification source: `liferepo/memory/`
- Private state source: `<private-repo>/memory/`

## Current Script Surface

Implementations currently live in:
- `skills/memory-ops/scripts/`

Legacy entrypoints remain in `<private-repo>/scripts/memory/` as wrappers that
delegate to this skill.
