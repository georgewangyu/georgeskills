---
name: cursor-chat-export-ops
description: Export Cursor chats into private artifacts for later search, review, and context recovery.
memory_tags:
  - domain:cursor
  - workflow:chat-export
  - repo_boundary:tools
  - data_class:private-derived
  - inputs:chat-history
  - outputs:markdown-export
  - risk:medium
---

# Cursor Chat Export Ops

## Trigger

Use when:
- the user wants to export Cursor chats
- the task needs archived AI chat context for later review or synthesis
- the request is specifically about Cursor chat history rather than email, notes, or X

## Workflow

1. Run the stable private wrapper:
   - `python3 scripts/exports/cursor-chats/export_cursor_chats.py`
2. Read the resulting files under:
   - `notes-private/cursor-chats/`
3. Summarize only the relevant sessions instead of dumping everything.

## Output Contract

- whether export succeeded
- where files landed
- any obvious path or permission blocker

## Guardrails

- Treat chat exports as private derived data.
- Keep summaries selective; the point is retrieval, not transcript spam.
