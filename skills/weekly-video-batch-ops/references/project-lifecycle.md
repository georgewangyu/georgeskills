# Video Project Lifecycle

Use explicit status instead of physically moving project folders. CapCut and
other editors can store absolute media paths, so the canonical project remains
in the batch where it was created.

## States

- `active`: filmed work that is still eligible for editing, export, or posting.
- `completed`: intentionally closed work. It appears in the originating
  batch's `_COMPLETED/` symlink view.
- `dropped`: intentionally abandoned work. It remains recoverable at its
  canonical path but is excluded from carryover and completed views.

`PROJECT_STATUS.json` in the project root is the machine-readable source of
truth. Projects without a manifest are `unclassified`; automation must report
them instead of guessing their state.

## Views

- `<origin-batch>/_COMPLETED/<project>` points to a completed canonical project.
- `<current-batch>/_CARRYOVER/<project>` points to an active project from a
  prior scanned batch.
- There is no `_ACTIVE/` mirror. Current-batch projects are already visible.
- There is no dropped folder. The status manifest is enough.

Both views contain symlinks only. Never move or copy raw media for a weekly
rollover, and never rename the canonical project merely to mark status.

## Commands

Dry-run before apply:

```bash
python3 scripts/manage_project_lifecycle.py set-status \
  --project <canonical-project-dir> \
  --status active \
  --dry-run
```

Use `completed` or `dropped` when George explicitly closes or abandons a
project. Add `--reason` for a useful human-readable decision note.

At weekly rollover:

```bash
python3 scripts/manage_project_lifecycle.py refresh-views \
  --media-root <media-root> \
  --current-batch <media-root>/_CURRENT_WEEK \
  --lookback-weeks 8 \
  --dry-run
```

Repeat with `--apply` only when the dry-run is coherent. The refresh creates
the current batch's `_COMPLETED/` and `_CARRYOVER/` navigation views, removes
only stale symlinks inside those views, and reports non-symlink conflicts.

## Automation Rules

1. Carry forward only projects explicitly marked `active`.
2. Exclude `completed` and `dropped` projects.
3. Do not infer completion from a final export or social post alone.
4. Do not infer abandonment from inactivity.
5. Report unclassified projects so George can make a one-time decision.
