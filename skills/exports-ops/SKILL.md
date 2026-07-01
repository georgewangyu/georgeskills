---
name: exports-ops
description: Umbrella skill for private export and import pipelines. Use this when the task spans multiple data sources or when no more specific export skill applies.
memory_tags:
  - domain:exports
  - workflow:data-ingestion
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - risk:high
---

# Exports Ops

## Trigger

Use this skill for reusable export/import automation:
- email/calendar exports
- Apple Notes and Cursor chat exports
- social feed ingestion/export
- multi-source export workflows that touch more than one data source

Prefer the narrower skills when the intent is clear:
- `x-check-ops`
- `email-ops`
- `calendar-ops`
- `apple-notes-export-ops`
- `cursor-chat-export-ops`

## Boundaries

- Specification source: `liferepo` workflow docs
- Private state source: `<private-repo>/captures/` and `<private-repo>/scripts/exports/*` config/token files

## Current Script Surface

Implementations currently live in:
- `skills/exports-ops/scripts/`

Legacy entrypoints remain in `<private-repo>/scripts/exports/` as wrappers that
delegate to this skill.
