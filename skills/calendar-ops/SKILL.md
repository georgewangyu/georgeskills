---
name: calendar-ops
description: Work with the private Google Calendar export pipeline for schedule context, day planning, and interview or journal prep.
memory_tags:
  - domain:calendar
  - workflow:calendar-export
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - inputs:calendar
  - outputs:markdown-export
  - risk:high
---

# Calendar Ops

## Trigger

Use when:
- the user wants calendar export or schedule context
- the task needs a day view before planning, journaling, or interview prep
- the workflow depends on fresh Google Calendar data under `<private-repo>/captures/calendar/`

Do not use when:
- the task is broad export prep across several sources; use `exports-ops`
- the user only wants a manual calendar opinion with no data pull

## Workflow

1. Run the stable private wrapper:
   - `python3 scripts/exports/calendar/export_calendar_google.py`
2. Read the newest artifacts under:
   - `captures/calendar/`
3. Distill the result into time constraints, meetings, travel/admin load, and open blocks.

## Output Contract

- whether export succeeded
- where exports landed
- main constraints and open time windows
- any missing-auth or token issues

## Guardrails

- Treat calendar exports as private derived data.
- Keep summaries operational and compact; raw event dumps are not the goal.
