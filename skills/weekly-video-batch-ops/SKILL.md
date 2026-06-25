---
name: weekly-video-batch-ops
description: Organize recurring short-form video batch production folders and final-export handling. Use when planning weekly TikTok, Instagram Reels, or YouTube Shorts batches; setting up batch/project media folders; handling CapCut export inboxes with awkward default names; normalizing final video names; creating quick-access final-video indexes; or refreshing weekly phone-transfer bundles.
memory_tags:
  - domain:social-media
  - workflow:weekly-video-batch
  - repo_boundary:tools
  - outputs:video-batch
  - risk:medium
---

# Weekly Video Batch Ops

## Purpose

Use this skill to keep short-form video production boring and repeatable:
plan a batch window, create project folders, route raw/imported media, and
normalize CapCut final exports without breaking editor references.

## Folder Model

Use one stable media root chosen by the user or private repo.

```text
<media-root>/
  _CURRENT_WEEK -> batches/YYYY/YYYY-Www_video-batch/
  batches/
    YYYY/
      YYYY-Www_video-batch/
        YYYY-MM-DD_video-slug/
          raw/
          assets/
          exports/
          final-videos/
          editor-projects/
  final-videos/
    incoming/
    index/
    by-week/
      YYYY-Www_video-batch/
    needs-review/
```

Rules:
- Use `YYYY-Www_video-batch`, not weekday-specific names. A batch can span
  filming, editing, export, and posting across multiple days.
- Treat `<media-root>/_CURRENT_WEEK` as a convenience symlink to the newest or
  selected active weekly batch. Refresh it whenever creating or switching the
  active weekly batch. If the path exists and is not a symlink, stop and report
  it instead of replacing a real directory.
- Keep one folder per video inside the batch.
- Shared scratch or raw-materials holding folders should not use the
  `YYYY-MM-DD_video-slug` pattern. Use a plain name like
  `general-raw-materials/` so it is visibly not an active video project, and do
  not add empty project subfolders unless they become useful.
- Keep raw footage in `raw/` only after import. Do not rename raw files unless
  duplicate collisions force it.
- Put generated overlays, screenshots, logos, and reference assets in `assets/`.
- Treat `exports/` as working exports, not the final library.
- Treat each project's `final-videos/` folder as the source of truth for final
  renders.
- Use `editor-projects/` for editor-side project shells, draft pointers, or
  import instructions. When creating a project folder, create a same-name empty
  editor project/shell when the local editor workflow supports it, or record the
  exact manual project name to create. Keep the shell empty until raw footage
  has been imported and the rough-cut direction is clear.
- Treat `<media-root>/final-videos/index/` as quick access only. Prefer
  symlinks to project-owned final files.
- Treat `<media-root>/final-videos/by-week/YYYY-Www_video-batch/` as the
  Finder-friendly phone-transfer bundle for that week. Prefer hard links there
  when the bundle and project finals are on the same volume, so AirDrop/Finder
  sees real files without duplicating storage. Use symlinks only when the user
  explicitly wants a reference-only bundle.
- When a video project is explicitly done, mark the project folder itself as
  complete by renaming it with a visible completion suffix such as
  `_complete`, unless the user or local runbook defines a different convention.
  Keep the original date and slug intact so sorting and search still work.
- If the project had old CapCut-facing paths or legacy notes, preserve those
  paths with compatibility symlinks when renaming the folder.

## CapCut Export Pattern

Do not require the creator to change CapCut export destinations for every
project.

Preferred pattern:
1. Set CapCut's export location once to:
   ` <media-root>/final-videos/incoming/`
2. Let CapCut produce awkward date/default names there.
3. During closeout, inspect the incoming files and map each export to the right
   batch project.
4. Move the accepted export into that project's `final-videos/` folder with a
   canonical name:
   `YYYY-MM-DD_video-slug_final_vNN.ext`
5. Create or refresh a symlink in `<media-root>/final-videos/index/`.
6. Refresh the weekly phone-transfer bundle:
   `<media-root>/final-videos/by-week/YYYY-Www_video-batch/`
   from the batch's project `final-videos/` folders.
7. Leave ambiguous exports in `final-videos/needs-review/` or report them
   without moving anything.

Never silently guess when two projects could plausibly own the same export.

## Weekly Workflow

1. Resolve local paths.
   - Find the private repo's current video plan or ask for it if missing.
   - If the private repo defines a weekday show calendar, format calendar, or
     recurring content slots, load that planning surface before selecting
     projects.
   - Find or create the media root from private config or user instruction.
   - Keep private absolute paths out of reusable skill files.
2. Create or update the batch.
   - Use the publish or production week as `YYYY-Www_video-batch`.
   - After the batch directory exists, refresh the current-week symlink:
     `scripts/refresh_current_week_symlink.py --media-root <media-root> --batch-dir <batch-dir> --dry-run`,
     then run the same command without `--dry-run` when it points at the
     intended batch.
   - Add one project folder per selected video.
   - For each selected video, also prepare a same-name empty editor project
     shell or editor-project pointer:
     `YYYY-MM-DD_video-slug`. Store shell metadata, links, or notes under that
     project's `editor-projects/` folder rather than scattering editor state.
     If the local editor automation can duplicate an empty template, run its
     dry-run first, then apply it only when the destination name is unambiguous.
     If no automation is available, leave a short manual instruction such as
     `Create empty editor project named YYYY-MM-DD_video-slug`.
   - When a weekday show calendar exists, keep each candidate tied to its slot
     in the weekly plan. Treat the slots as coverage guidance, not as required
     folders or a forced posting quota.
   - Keep shared raw-materials folders separate from selected-video folders.
   - Put next-week candidates in the next batch, not the current batch.
3. Prepare imports.
   - Keep active project folders scoped to the current batch.
   - If clips may serve multiple videos, keep them in the batch or project
     where they are first imported and copy only after the winning edit is
     known.
4. Handle final exports.
   - Scan `final-videos/incoming/` for recent video files.
   - Map each export to a project using creator notes, timestamps, project
     names, script titles, or explicit user confirmation.
   - Build a mapping JSON before moving/renaming files.
   - Run `scripts/normalize_final_videos.py --mapping <mapping.json> --dry-run`
     first.
   - Run the same command without `--dry-run` only after the mapping is
     coherent.
   - Run `scripts/refresh_weekly_transfer_bundle.py --batch-dir <batch-dir>
     --transfer-dir <media-root>/final-videos/by-week/YYYY-Www_video-batch
     --clean --dry-run`, then apply it when the planned bundle is right.
5. Close the batch.
   - Record final paths, posted links, and unresolved exports in the weekly
     plan or private log.
   - Make sure the weekly phone-transfer bundle contains every final media file
     the creator may need to copy or AirDrop to a phone.
   - Rename completed project folders according to the local completion
     convention, then update any weekly plan paths that pointed at the old
     folder name.
   - Preserve compatibility symlinks for old CapCut-facing paths when a
     completed-folder rename would otherwise break them.
   - Carry unused but good topics into the next batch plan.

## Mapping File

Use this shape for final-video normalization:

```json
{
  "incoming_dir": "<media-root>/final-videos/incoming",
  "batch_dir": "<media-root>/batches/2026/2026-W26_video-batch",
  "final_index_dir": "<media-root>/final-videos/index",
  "items": [
    {
      "source": "0624.mp4",
      "project": "2026-06-24_ai-vampire-agent-fatigue",
      "canonical_name": "2026-06-24_ai-vampire-agent-fatigue_final_v01.mp4"
    }
  ]
}
```

`source` may be absolute or relative to `incoming_dir`.
`project` may be absolute or relative to `batch_dir`.

## Output Contract

Return:
- batch folder path
- current-week symlink path and refresh status
- per-video project folder list
- per-video editor project shell or manual editor-project creation status
- show-slot coverage status, when a weekday show calendar exists
- CapCut export inbox path
- weekly phone-transfer bundle path
- final-video mapping status
- dry-run command and result for any normalization
- transfer-bundle refresh command and result
- unresolved exports that need human review
- weekly automation status, when relevant

## Guardrails

- Do not move legacy media trees without explicit approval.
- Do not create or overwrite editor projects in an application's private
  library unless the local workflow explicitly supports safe project creation,
  dry-run/backup, and same-name collision handling.
- Do not rename project folders that may still be referenced by an active editor
  project unless the user explicitly calls the video done or the local runbook
  says the closeout rename is safe.
- Do not break old editor references. If old projects reference old absolute
  paths, preserve those paths with compatibility symlinks or leave the old tree
  in place.
- Do not hard-code private local paths, account handles, or creator identity in
  this skill.
- Do not delete CapCut exports during normalization.
- Do not overwrite final videos unless explicitly instructed.
