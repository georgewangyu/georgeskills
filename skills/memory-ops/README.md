# Memory Scripts

**Genesis**: Created when the new `memory/` layer stopped being just a schema
idea and needed an actual extraction path from daily summaries.

## Purpose

This directory contains automation for the structured memory system.

Current focus:

- extract conservative memory candidates from daily summaries
- validate memory files
- later support querying, reinforcement, and promotion workflows

## Current Scripts

- `extract_daily_summary_candidates.py`
  - Reads one or more daily summaries
  - Extracts conservative `candidate` records for:
    - `decision`
    - `commitment`
    - `status_change`
    - `pattern`
  - Writes per-day candidate JSONL files under `memory/candidates/`
- `validate_memory_records.py`
  - Checks canonical and candidate JSONL files for parse errors and required fields
- `promote_memory_candidates.py`
  - Promotes reviewed candidates into canonical stores by id or whole file

## Operating Model

- Canonical stores live under `memory/*.jsonl`
- Candidate extraction writes to `memory/candidates/`
- Human review should happen before candidates are promoted into canonical
  stores

## Why Conservative

Good memory tooling should not flood the system with junk just because a model
can emit lots of records.

The extractor intentionally starts with sections that are already semantically
strong in the daily-summary format:

- `Key Decisions`
- `Tomorrow`
- `Conversation Milestones`
- `Challenges`
- `Narrator Notes`
