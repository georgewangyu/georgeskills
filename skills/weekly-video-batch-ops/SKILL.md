---
name: weekly-video-batch-ops
description: Organize recurring short-form video batch production folders, correctly named empty CapCut draft shells, final-export handling, and owned-platform posting audits. Use when planning weekly TikTok, Instagram Reels, or YouTube Shorts batches; setting up a canonical video project; the creator says they are about to start editing; handling CapCut export inboxes with awkward default names; normalizing final video names; creating quick-access final-video indexes; refreshing weekly phone-transfer bundles; or checking which final videos have already been posted.
memory_tags:
  - domain:social-media
  - workflow:weekly-video-batch
  - skill_role:operator
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
- Use the weekly batch folder itself as the project navigation surface. Do not
  create or maintain an `_ACTIVE/` folder just to mirror projects that are
  already visible in the batch. Preserve an existing `_ACTIVE/` compatibility
  path or alias only when it is still referenced by CapCut or another tool.
- Shared scratch or raw-materials holding folders should not use the
  `YYYY-MM-DD_video-slug` pattern. Use a plain name like
  `general-raw-materials/` so it is visibly not an active video project, and do
  not add empty project subfolders unless they become useful.
- Keep raw footage in `raw/` only after import. Do not rename raw files unless
  duplicate collisions force it.
- Put generated overlays, screenshots, logos, and reference assets in `assets/`.
- Default new project folders to only `raw/` and `assets/`. Add a working
  subfolder only when real files require it; do not pre-create empty
  `exports/`, `final-videos/`, or `editor-projects/` folders.
- Treat `<media-root>/final-videos/by-week/YYYY-Www_video-batch/` as the source
  of truth for newly accepted final renders. Existing project-owned finals may
  remain in place for compatibility; do not migrate them just for tidiness.
- Use an optional `editor-projects/` for editor-side project shells, draft pointers, or
  import instructions. When creating a canonical project folder, or as soon as
  the creator says editing is about to begin, create a same-name empty editor
  project/shell when the verified local workflow supports it. Do this before
  the editor creates a date-only default. Keep the shell empty until raw footage
  is imported and the creator has chosen the A-roll/story cut.
- Treat `<media-root>/final-videos/index/` as the global quick-access view.
  Every accepted final must have one healthy symlink here, whether the backing
  file is a legacy project final or a centrally owned weekly final.
- Do not require a separate active/done folder state. When the creator
  explicitly says a project is complete and a visible marker would help, the
  project folder may be renamed with a suffix such as `_complete`, unless the
  local runbook defines a different convention. Keep the original date and
  slug intact so sorting and search still work.
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
4. Move the accepted export into the central weekly final folder with a
   canonical name:
   `YYYY-MM-DD_video-slug_final_vNN.ext`
5. Create or refresh a symlink in `<media-root>/final-videos/index/`.
6. Leave ambiguous exports in `final-videos/needs-review/` or report them
   without moving anything.

Never silently guess when two projects could plausibly own the same export.

## CapCut Draft Bootstrap

Treat empty named draft creation as project setup, not timeline editing.
Creating the shell establishes the canonical name early; it does not import
media, cut silence, arrange A-roll, add captions, place assets, or make creative
edit decisions.

Use the local `capcutbot` duplicate command only after verifying its current
environment and an actually empty source template:

1. Resolve the editor-owned draft library with `capcutbot env` or
   `CAPCUTBOT_DRAFTS_DIR`. The root may be outside the media batch and may be on
   an external volume; pass the resolved absolute root rather than assuming the
   default CapCut location.
2. Select a trusted empty template whose draft JSON has zero duration and no
   timeline tracks. Do not infer emptiness from a filename containing
   `template`, `blank`, or `empty`.
3. CapCut may remain open when the destination is a new, uniquely named draft.
   Do not overwrite an existing destination. Record whether CapCut was running
   and tell the creator that the new draft may require a project-list refresh
   or app restart before it appears.
4. Run the bundled wrapper first with `--dry-run`, inspect the source, target,
   collision state, and resolved draft root, then rerun with `--apply`:

```bash
python3 scripts/prepare_capcut_draft.py \
  --project-dir <batch-dir>/YYYY-MM-DD_video-slug \
  --drafts-root <resolved-capcut-drafts-root> \
  --empty-template <empty-template-name-or-path> \
  --capcutbot-dir <capcutbot-repo> \
  --dry-run

python3 scripts/prepare_capcut_draft.py \
  --project-dir <batch-dir>/YYYY-MM-DD_video-slug \
  --drafts-root <resolved-capcut-drafts-root> \
  --empty-template <empty-template-name-or-path> \
  --capcutbot-dir <capcutbot-repo> \
  --apply
```

The wrapper must stop on a noncanonical project name, nonempty template,
existing target, existing receipt, or missing draft root. An open CapCut
process is informational for a uniquely named destination, not an app-wide
block.
Successful creation leaves `editor-projects/capcut-draft.json` as the durable
pointer/receipt. Draft creation is copy-only: the template is not modified, the
destination is never overwritten, and therefore no backup is necessary for the
new shell. Any later JSON mutation is a separate timeline-editing operation and
must use CapCutBot's dry-run plus timestamped backup behavior.

For an existing date-only or otherwise legacy CapCut draft, do not repair the
name by renaming only its folder. Use the migration helper so the folder,
`draft_meta_info.json`, and embedded absolute draft paths stay in sync while
the untouched original becomes a timestamped backup:

```bash
python3 scripts/migrate_capcut_draft_name.py \
  --drafts-root <absolute-active-drafts-root> \
  --current-name '<legacy-name>' \
  --canonical-name YYYY-MM-DD_video-slug \
  --project-dir <batch-dir>/YYYY-MM-DD_video-slug \
  --backup-root <same-volume-capcut-backup-root> \
  --dry-run
```

Review the JSON change list and source fingerprint, then repeat with `--apply`.
The helper refuses collisions, mismatched metadata, cross-volume backup moves,
and noncanonical project names. If CapCut is open or a `.locked` marker exists,
the helper records a warning because an actively open source draft can follow
last-writer-wins behavior; prefer creating a new version instead of migrating
the draft currently visible in the editor. It writes or replaces
`editor-projects/capcut-draft-migration.json` only after validation succeeds.

If no trusted empty template or safe automation is available, do not duplicate
an arbitrary old draft. Write the exact canonical project name into
`editor-projects/` as a manual creation instruction and report the blocker.

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
   - Add one project folder per selected video, with only `raw/` and `assets/`
     by default. The operator should create the folder so its ISO date, slug,
     week placement, and dashboard entry stay aligned.
   - Prepare a same-name empty CapCut shell `YYYY-MM-DD_video-slug` only when
     the creator says editing is about to begin. Follow the
     CapCut Draft Bootstrap gate above: inspect the configured draft root and
     empty template, dry-run, and collision-check, then apply to a unique
     destination. CapCut may stay open; surface the possible refresh/restart
     step. If the gate cannot pass, record the exact manual project name in
     the weekly plan and report the blocker; do not create an empty pointer
     folder just to hold a note.
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
   - Set `accepted_final_dir` in the mapping to
     `<media-root>/final-videos/by-week/YYYY-Www_video-batch` for the lean
     central-final model. Use `refresh_weekly_transfer_bundle.py` only for
     legacy batches whose finals still live inside project folders.
5. Close the batch.
   - Record final paths, posted links, and unresolved exports in the weekly
     plan or private log.
   - Make sure the weekly phone-transfer bundle contains every final media file
     the creator may need to copy or AirDrop to a phone.
   - When the user asks which videos have been posted, which finals still need
     posting, or what remains for the week, run an owned-platform posting audit
     instead of relying only on the plan. Prefer configured local tools such as
     `igbot my-media --max-results <n> --format json` and
     `tiktokbot my-videos --max-results <n> --format json` when available;
     otherwise use the relevant platform-check skill or clearly report the
     missing data source.
   - Compare recent owned Instagram/TikTok posts against the final-video
     bundle, project slugs, captions, dates, and known same-day exceptions.
     Record matched links and mark unmatched finals as `needs posting`, not as
     done.
   - Rename completed project folders according to the local completion
     convention, then update any weekly plan paths that pointed at the old
     folder name.
   - Preserve compatibility symlinks for old CapCut-facing paths when a
     completed-folder rename would otherwise break them.
   - Carry unused but good topics into the next batch plan.

## Pre-Filming Reaction Batch

Use this when the weekly workflow includes a recurring reaction-filming block,
especially a midweek session built from posts, videos, comments, transcripts,
or other source material the creator saw during the day.

This is not a posting calendar. It is a read-through packet for filming.

1. Start with inventory.
   - List already filmed or already edited videos first, so the creator does
     not refilm ideas that are already covered.
   - List carryover edits separately from fresh filming candidates.
   - If the next several publish slots are already covered, say so and do not
     force new candidates just because the calendar has open slots.
2. Build the fresh reaction queue.
   - Pull candidates from the creator's saved posts, observed videos, source
     links, transcripts, daily notes, or explicit user picks.
   - Keep the queue short enough to film. Prefer `3-5` likely candidates over
     a long archive.
   - Treat show slots or content categories as tags, not obligations.
3. For each candidate, capture the minimum decision packet:
   - working title
   - tags such as `reaction`, `personal story`, `on-call`, `demo`, `receipt`,
     `creator-process`, or `sponsor`
   - source object or source note
   - the creator's take in one sentence
   - proof object or first visual frame
   - production burden: `talking-head`, `green-screen/source card`,
     `screen recording`, `B-roll`, or `edit-only`
   - status: `selected to film`, `backup`, `already filmed`, `edit pickup`,
     or `parked`
   - next action
4. Prepare the read-through packet before the filming block.
   - For each selected reaction candidate, write `3-4` hook options.
   - Pick one recommended hook before filming unless the creator asks to decide
     live.
   - Add `2-3` beat bullets and a twist/payoff.
   - Include first-frame and on-screen-text guidance when a source post or
     screenshot anchors the reaction.
5. Keep the packet separate from the backlog.
   - Park unused candidates in the weekly plan or private notes, but do not let
     them crowd the filming packet.
   - The filming packet should answer: "What am I reading through and filming
     today?"

## Video Brief Shape

When creating or updating per-video planning Markdown, start with the smallest
usable creative unit before any longer production notes:

```text
## Hook / Beat / Twist

- Hook: [one spoken/on-screen opener]
- Beat 1: [first concrete progression beat]
- Beat 2: [second concrete progression beat]
- Twist: [payoff, turn, or button]
```

Keep this block near the top, directly after the title/frontmatter. Longer
sections such as shot lists, captions, sponsor notes, proof assets, and folder
paths can follow, but they should not hide the hook, main beats, or twist. If
the user is trying to review or choose videos quickly, prefer this compact
block over a long script.

For a reaction candidate that will be filmed in a batch, use a slightly richer
but still compact shape:

```text
## Filming Packet

- Source:
- Take:
- Recommended hook:
- Hook options:
  - [option 1]
  - [option 2]
  - [option 3]
  - [optional option 4]
- Beat 1:
- Beat 2:
- Beat 3:
- Twist:
- First frame / proof object:
```

Avoid writing a long script unless the creator asks for one. The goal is to
give the creator something sharp enough to read through, internalize, and film
naturally.

## Reminder Cadence

When a creator has a known weekly filming block, prepare the read-through packet
the prior evening or at least before the filming window. The reminder should
name the likely videos to film, identify which ones are already filmed or only
need edits, and link or summarize the compact filming packets. Do not send a
long candidate archive as the reminder.

## Mapping File

Use this shape for final-video normalization:

```json
{
  "incoming_dir": "<media-root>/final-videos/incoming",
  "accepted_final_dir": "<media-root>/final-videos/by-week/2026-W26_video-batch",
  "final_index_dir": "<media-root>/final-videos/index",
  "items": [
    {
      "source": "0624.mp4",
      "canonical_name": "2026-06-24_ai-vampire-agent-fatigue_final_v01.mp4"
    }
  ]
}
```

`source` may be absolute or relative to `incoming_dir`.
With `accepted_final_dir`, `canonical_name` is required and `project` is
optional. For compatibility with older project-owned libraries, omit
`accepted_final_dir` and provide `batch_dir` plus `project`.

## Output Contract

Return:
- batch folder path
- current-week symlink path and refresh status
- per-video project folder list
- per-video editor project shell or manual editor-project creation status
- resolved CapCut draft root, empty-template source, dry-run result, and
  `editor-projects/capcut-draft.json` receipt path when a shell was created,
  including source/target fingerprints, whether CapCut was running, and any
  refresh/restart warning
- show-slot coverage status, when a weekday show calendar exists
- pre-filming reaction packet status, when the task involves a reaction batch
- CapCut export inbox path
- weekly phone-transfer bundle path
- final-video mapping status
- owned-platform posting audit status, including tools used and matched /
  unmatched finals when the task involves posting state
- dry-run command and result for any normalization
- transfer-bundle refresh command and result
- unresolved exports that need human review
- weekly automation status, when relevant

## Guardrails

- Do not move legacy media trees without explicit approval.
- Do not create or overwrite editor projects in an application's private
  library unless the local workflow explicitly supports safe project creation,
  dry-run/backup, and same-name collision handling.
- Do not overwrite or reuse an existing CapCut destination. A uniquely named
  new-version draft may be created while CapCut is open; retain source/target
  fingerprints and surface any project-list refresh or restart needed. Do not
  use a nonempty project as the empty-shell template.
- Do not describe an empty named draft as an edited timeline. A-roll assembly,
  silence cuts, asset placement, captions, and creative pacing remain separate
  work.
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
