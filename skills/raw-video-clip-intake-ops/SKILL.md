---
name: raw-video-clip-intake-ops
description: Sort raw camera-card clips into the right short-form video project folders. Use when a creator says they filmed several videos on a DJI/camera card or external drive and needs the clips grouped by topic, separator shots, timestamp order, or spoken context into weekly batch folders while preserving raw sidecars such as MP4, WAV, LRF, SRT, or proxy files and writing intake manifests before rough-cut editing.
memory_tags:
  - domain:social-video
  - workflow:raw-clip-intake
  - skill_role:operator
  - repo_boundary:tools
  - inputs:camera-card
  - outputs:intake-manifest
  - risk:medium
---

# Raw Video Clip Intake Ops

## Purpose

Turn a messy camera card into project-owned raw folders without losing sidecars
or making future editing agents rediscover what each take was.

Use this before `shortform-rough-cut-ops`. This skill answers: "Which raw files
belong to which video project?" Rough-cut skills answer: "What should survive
inside those clips?"

## Core Rule

Do not delete or rename source-card files during intake. Copy or hard-link raw
sidecar sets into project folders, then write an `INTAKE.md` manifest with the
source path, grouping rationale, clip list, durations, and uncertainty.

## Workflow

1. Resolve context.
   - Identify the source card/folder.
   - Identify the destination weekly batch folder.
   - Identify the intended video topics and their rough filming order.
   - Load the relevant weekly video plan or private video-operator ledger when
     available, because project slugs may already exist.
2. Inventory the source.
   - List candidate video files by timestamp and filename order.
   - Preserve sidecar relationships by shared stem, such as `.MP4`, `.WAV`,
     `.LRF`, `.SRT`, and proxy files.
   - Use `ffprobe` for duration/resolution when available.
   - Build a contact sheet when visual grouping matters.
3. Infer groups.
   - Use filename order and capture timestamps as the first pass.
   - Use user-stated topic order as a strong signal.
   - Use short clips, camera-bag shots, phone/prop shots, repeated setup shots,
     and long gaps as separators.
   - Treat long talking-head clips as likely main takes; treat very short clips
     as setup, false starts, separators, or pickups until confirmed.
   - If two adjacent groups are ambiguous, stop and ask for confirmation before
     copying, or copy into a clearly labeled `needs-review` folder.
4. Create destination folders.
   - Use the existing local batch shape when present:

     ```text
     YYYY-MM-DD_video-slug/
       raw/
       assets/
       editor-projects/
       exports/
       final-videos/
     ```

   - Do not hard-code local media roots in the reusable skill. Resolve them
     from user input or private repo config.
5. Copy sidecar sets.
   - Copy every file sharing the selected clip stem into that project's `raw/`
     folder.
   - Prefer non-destructive copy by default. Use hard links only when the user
     asks and the source/destination are on the same volume.
   - Run a dry-run first when the grouping was inferred rather than explicitly
     supplied.
6. Write manifests.
   - Add `INTAKE.md` to each project root.
   - Include source folder, destination, copy mode, original files left in
     place, clip durations, separator notes, and unresolved questions.
7. Update private state.
   - Record created project folders in the weekly plan or video-operator
     ledger.
   - Capture workflow friction that should improve the next version of the
     skill, such as slow external-drive copies or missing labels.

## Script

Use `scripts/intake_camera_card.py` for deterministic inventory, dry-runs,
copying, and manifest generation.

Example grouping plan:

```json
{
  "groups": [
    {
      "slug": "2026-07-08_story-time-example",
      "title": "Story Time Example",
      "clip_ids": ["0008", "0009", "0010"],
      "notes": {
        "0008": "short lead-in",
        "0009": "false start or pickup",
        "0010": "main take"
      }
    }
  ]
}
```

Dry-run:

```bash
python scripts/intake_camera_card.py \
  --source-dir "<camera-card>/DCIM/DJI_001" \
  --batch-dir "<media-root>/batches/YYYY/YYYY-Www_video-batch" \
  --groups-json grouping-plan.json \
  --dry-run
```

Apply:

```bash
python scripts/intake_camera_card.py \
  --source-dir "<camera-card>/DCIM/DJI_001" \
  --batch-dir "<media-root>/batches/YYYY/YYYY-Www_video-batch" \
  --groups-json grouping-plan.json \
  --apply
```

Generate a contact sheet during inventory:

```bash
python scripts/intake_camera_card.py \
  --source-dir "<camera-card>/DCIM/DJI_001" \
  --inventory \
  --contact-sheet /tmp/camera-card-contact-sheet.jpg
```

## Output Contract

Return:

- source folder inspected
- destination batch folder
- grouping table: project slug, clip IDs, file count, size
- created or reused project folders
- manifest paths
- unresolved grouping uncertainty
- next editing step, usually transcription-first A-cut with
  `shortform-rough-cut-ops`

## Guardrails

- Never delete source-card files.
- Never copy private raw footage into a public git repo.
- Do not rename raw clip files during intake unless collision handling requires
  a suffix.
- Do not silently drop sidecars.
- Do not treat a camera-bag separator as proof by itself; combine it with
  timestamp order, user topic order, and clip duration.
- If a source file is still being written or a copy leaves temporary files,
  stop and verify before continuing.
