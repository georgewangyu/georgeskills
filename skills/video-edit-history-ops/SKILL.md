---
name: video-edit-history-ops
description: Load relevant lessons before a video edit, create a durable history receipt when an AI-assisted edit becomes reviewable, and update it after creator feedback or publication. Use when starting or resuming an edit, producing a reviewable AI edit, receiving review notes, diagnosing a repeated editing failure, reconciling weekly video projects against a history index, capturing an editor preset, or promoting a project lesson into a reusable default.
metadata:
  memory_tags:
    - domain:video
    - workflow:video-edit-history
    - skill_role:operator
    - repo_boundary:tools
    - inputs:video-project
    - outputs:history-receipt
    - risk:medium
    - data_class:private-derived
---

# Video Edit History Ops

Carry editing judgment across projects without copying raw media into a memory
repository or turning one-off preferences into universal rules.

## Required Inputs

- `history_root`: private creator-specific history repository
- current video id, format, project path, and editor
- current stage: intake, A-roll, visual pass, native assembly, review, or final
- relevant project artifacts and fingerprints
- exact creator feedback when writing history

If no history root exists, propose a private location and schema. Do not place
creator-specific history in a reusable or public skill repository.

## Before Editing

1. Read the history index and promoted defaults.
2. Filter by format, series, editor, visual treatment, and known failure risk.
3. Load only the most relevant detailed entries.
4. Add the applicable lessons and failure checks to the project's intake or
   gate ledger.
5. Keep `project_only`, `candidate`, and `promoted` lessons distinct.

Do not silently apply a historical choice that conflicts with the current
brief, current footage, or explicit creator instruction.

## Two-Stage Capture

### Stage 1: First Reviewable AI Edit

Do not wait for publication or project closeout. As soon as an AI-assisted edit
has an artifact that the creator can meaningfully review:

1. Create the detailed per-video record from inspectable evidence.
2. Add its row to the history index in the same change.
3. Add `AI_EDIT_HISTORY.md` to the external video project. The pointer must
   contain:
   - `schema: ai-edit-history-pointer-v1`
   - the stable `video_id`
   - the record path relative to `history_root`
   - `capture_stage`
   - `captured_at`
4. Record the exact review artifact, project/editor links, software, launched
   sessions or evidenced lanes, approval boundary, and candidate learnings.
5. Add the history-record pointer to the active production ledger when one
   exists.

The record may remain `review`, `human-polish`, or another truthful in-progress
state. Unknown counts and open creator decisions are valid; a missing record is
not.

### Stage 2: Feedback And Closeout

1. Identify the exact reviewed artifact, duration, fingerprint, and approval
   boundary.
2. Record feedback with timestamps and problem phrases when available.
3. Separate observed evidence, creator statements, and agent interpretation.
4. Explain why each meaningful failure passed the earlier gate.
5. Update the per-video record and history index in the same change.
6. Update the failure registry when a new detection gate is now justified.
7. Promote a default only when the creator explicitly requests it or at least
   two independently reviewed edits support it.
8. Update the project-side `AI_EDIT_HISTORY.md` capture stage and next trigger.

Use the schema in [history-schema.md](references/history-schema.md).

## Weekly Reconciliation

The per-edit write is the primary path. Use the weekly reconciliation only as a
safety net for missed or broken receipts.

Run:

```bash
python3 scripts/reconcile_history.py \
  <history_root> \
  <current-video-batch-root> \
  <previous-video-batch-root>
```

The command is read-only. It reports:

- reviewable projects missing `AI_EDIT_HISTORY.md`
- pointers whose detailed record is missing
- pointer and record `video_id` mismatches
- detailed records missing from the index

Do not auto-create history from filenames or render presence alone. Resolve
each issue from the project brief, reviewed artifact, thread/session receipts,
and exact creator feedback, then rerun the reconciliation.

## Preset Capture

When the creator wants an editor filter/effect preset remembered:

- capture exact native names, values, intensity, ordering, scope, and
  applicability
- link the verified source draft and reference export
- distinguish unknown values from zero or disabled values
- version the preset
- require native persistence or a verified readback before calling it captured

Do not infer exact preset values from the appearance of a compressed render.

## Backfill

An index may list older known edits before full records exist. Mark them
`backfill`; do not invent lessons from filenames, publication receipts, or
vague memory. Backfill only from inspectable evidence or explicit feedback.

## Output Contract

Return or maintain:

- updated history index
- one detailed per-video record for the reviewed edit
- project-side `AI_EDIT_HISTORY.md` pointer
- changes to promoted defaults or failure modes, if justified
- preset record, when exact values were captured
- project-ledger pointer to the history record
- unresolved taste, pickup, rights, or tooling issues

Run `scripts/validate_history.py <history_root>` before handoff.
When project roots are available, also run
`scripts/reconcile_history.py <history_root> <project-root> [...]`.

## Guardrails

- Never copy raw footage, full transcripts, large assets, renders, or editor
  graphs into the history repository.
- Never mutate creator-owned media or drafts while recording history.
- Never label an experimental candidate as creator-approved.
- Never promote a one-off interpretation without the required evidence.
- Keep reusable procedure here and private creator memory in the supplied
  history root.
