---
name: journal-ops
description: Modular tooling for journal ingestion, prep, and derived-context generation. Use when work involves reusable journal processing logic.
memory_tags:
  - domain:journal
  - workflow:daily-summary
  - skill_role:operator
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
- `skills/journal-ops/config/daily_workflow_modules.yml` defines the module
  profiles used to keep daily workflow prep lightweight without changing the
  normal output contract.

Legacy entrypoints remain in `<private-repo>/scripts/journal/` as wrappers that
delegate to this skill.

The prep runner discovers transcript sources and refreshes objective context;
it does not interpret transcripts or call an external model provider. The
active Codex agent must read the available transcript text directly, interpret
all same-day sources together, and write the most useful supported synthesis
into the private journal.

The standard and full prep profiles also create a bounded private iMessage
daily-context staging file through `exports-ops`. Treat it like transcript
source material: the active Codex agent interprets it, but only derived
day-level context belongs in the journal. The check-in profile skips Messages.
