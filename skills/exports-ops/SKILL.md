---
name: exports-ops
description: Modular tooling for private data export/import pipelines (email, calendar, Apple Notes, Cursor chats, social feeds).
memory_tags:
  - domain:exports
  - workflow:data-ingestion
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

## Boundaries

- Specification source: `liferepo` workflow docs
- Private state source: `<private-repo>/notes-private/` and `<private-repo>/scripts/exports/*` config/token files

## Current Script Surface

Implementations currently live in:
- `skills/exports-ops/scripts/`

Legacy entrypoints remain in `<private-repo>/scripts/exports/` as wrappers that
delegate to this skill.
