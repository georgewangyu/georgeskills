# Video Edit History Schema

## Repository Minimum

```text
history/INDEX.md
history/YYYY/YYYY-MM-DD_slug.md
registries/EDITING_DEFAULTS.md
registries/FAILURE_MODES.md
presets/
templates/VIDEO_HISTORY_ENTRY.md
```

Every reviewable external project should also contain:

```text
AI_EDIT_HISTORY.md
```

## Required Frontmatter

- `schema: video-edit-history-v1`
- `video_id`
- `title`
- `reviewed_at`
- `status`
- `lesson_status`: `project_only`, `candidate`, `promoted`, or `superseded`
- `tags`

## Required Sections

- `Evidence`
- `Creator Feedback` or an explicitly named creator-feedback heading
- `Failure Analysis`
- `Reusable Lessons`
- `Next Iteration`

The evidence section should identify the exact reviewed artifact and approval
boundary. Use hashes when available, but do not copy the artifact.

## Index Fields

- video title
- review date
- production stage
- record link or `backfill`
- search tags
- one high-signal lesson, clearly labeled when tentative

## Project Pointer

Required frontmatter:

- `schema: ai-edit-history-pointer-v1`
- `video_id`: must match the detailed record
- `history_record`: path relative to `history_root`; it must resolve beneath
  `history/` and must not be absolute, traverse out of that directory, or
  escape through a symlink
- `capture_stage`: normally `reviewable`, `creator-selected`, `final`, or
  `published`
- `captured_at`: `YYYY-MM-DD`

The body should identify the current reviewed artifact, approval boundary, and
next update trigger. The pointer stores no raw media, transcript, render, or
editor graph.

## Promotion Evidence

Every promoted default must link to either:

- an explicit creator statement that it is the future default; or
- two independently reviewed video records supporting the same rule.
