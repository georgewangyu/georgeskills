---
name: apple-notes-export-ops
description: Export Apple Notes into private markdown artifacts for downstream search, journaling, and context-building workflows.
memory_tags:
  - domain:notes
  - workflow:notes-export
  - repo_boundary:tools
  - data_class:private-derived
  - inputs:notes
  - outputs:markdown-export
  - risk:high
---

# Apple Notes Export Ops

## Trigger

Use when:
- the user wants a fresh Apple Notes export
- the workflow depends on note context before journaling or synthesis
- the task is specifically about notes export rather than email or calendar

## Workflow

1. Run the stable private wrapper:
   - `python3 scripts/exports/apple-notes/export_apple_notes.py`
2. Read the resulting files under:
   - `captures/apple-notes/`
3. Pull only the notes relevant to the target date or topic.

## Output Contract

- whether the export succeeded
- where files landed
- any obvious missing-permission or automation blockers

## Guardrails

- Treat exported notes as private derived data.
- Prefer topic/date filtering instead of loading a huge note corpus blindly.
