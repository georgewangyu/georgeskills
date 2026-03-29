---
name: journal-ops
description: Modular tooling for journal ingestion, prep, and derived-context generation. Use when work involves reusable journal processing logic.
memory_tags:
  - domain:journal
  - workflow:daily-summary
  - repo_boundary:tools
  - data_class:private-derived
  - risk:medium
---

# Journal Ops

## Trigger

Use this skill when implementing reusable journal tooling such as:
- context generation
- metrics ingestion
- workflow prep orchestration
- workflow completeness checks
- sprint metrics visualization

## Boundaries

- Specification source: `liferepo/journal/`
- Private state source: `<private-repo>/journal/`
- This skill should stay data-agnostic where possible.

## Current Script Surface

Implementations currently live in:
- `skills/journal-ops/scripts/`

Legacy entrypoints remain in `<private-repo>/scripts/journal/` as wrappers that
delegate to this skill.
