---
name: video-asset-pack-ops
description: Turn a settled short-form video script, transcript, or beat outline into a sourced, editor-ready asset pack. Use when editing is about to begin and the project needs screenshots, posts, articles, benchmarks, photos, logos, product UI, official clips, proof receipts, a numbered asset folder, or a beat-to-asset manifest; also use proactively after script lock when the user has signaled that filming or editing is underway.
memory_tags:
  - domain:social-media
  - workflow:video-asset-pack
  - skill_role:operator
  - repo_boundary:tools
  - inputs:script
  - outputs:asset-pack
  - risk:medium
---

# Video Asset Pack Ops

Build the proof and context layer for a video before the timeline is polished. Preserve source fidelity, fan out independent collection lanes early, and leave the editor with numbered assets plus an exact shot map.

## Input Gate

Resolve:

- settled script, transcript, or stable beat outline
- target video project or output directory
- target duration and aspect ratio when known
- existing imported-media paths that must remain stable
- any named must-have assets

Treat the script as locked enough when its claims, order, and hook are stable even if filler words or final captions may still change.

If the user is merely discussing a script, offer the asset pass in one sentence. If the user says they are editing, has recorded the script, or asks for assets, begin without another confirmation. Do not start paid generation or large media downloads under this implicit trigger.

## Workflow

### 1. Protect the project structure

- Use the active video-folder convention from the invoking workspace. If the project does not exist, invoke `weekly-video-batch-ops` to create it.
- When a canonical project is created or the creator says editing is about to begin, have `weekly-video-batch-ops` bootstrap the same-name empty CapCut draft immediately. Complete its dry-run, collision, empty-template, unique-target, and fingerprint gates before applying. CapCut may remain open for a new uniquely named draft; surface any project-list refresh or restart needed. Do not wait until export or cleanup to repair a date-only editor name.
- Never rename or move a folder already imported into an editor unless explicitly authorized.
- When a canonical project name is useful, have `weekly-video-batch-ops` create it and preserve the imported path with a compatibility symlink or pointer.
- Put gathered material in the project's `assets/` directory. Keep raw footage and final exports out of it.
- Delegate folder creation and batch conventions to `weekly-video-batch-ops` when that skill applies.
- Treat the resulting `editor-projects/capcut-draft.json` as a project pointer, not proof that any timeline editing was completed.

### 2. Convert the script into asset beats

For every spoken beat, identify:

- claim or emotional job
- best proof object
- fallback visual
- preferred treatment: full screen, punch-in, split screen, picture-in-picture, screen recording, motion, or A-roll only
- likely on-screen duration
- accuracy risk: live metric, disputed claim, time-sensitive rank, or opinion

Do not gather generic decoration until the proof beats are covered.
For talking-head footage, default proof to a face-safe partial-frame overlay.
Budget zero or one full-screen takeover for the short; it must perform a
legibility-critical proof job or a meaningful multi-state explanation. Reject
static full-screen cards and single-state scale loops over the speaker.

### 3. Allocate filenames before collection

Number assets in intended story order:

`NN_short_descriptive_slug.ext`

Give each worker exclusive filenames or a separate staging folder. Reserve gaps rather than letting workers overwrite each other. Record the source URL and capture time as soon as an asset is accepted.

### 4. Fan out independent lanes immediately

Use available subagents proactively when the runtime permits it. Default to at least three parallel lanes when four or more independent assets exist:

1. social posts and live metrics
2. articles, official announcements, benchmarks, pricing, and product UI
3. transcript-to-asset mapping and claim checking
4. higher-order visual concepts or final QA

Keep the parent responsible for project paths, collision avoidance, visual inspection, manifest synthesis, and user handoff. Do not make several workers fight the same blocked page. See [subagent-lanes.md](references/subagent-lanes.md) for lane contracts.

Prefer existing browser runtimes, direct public embeds, public APIs, or lightweight HTTP before installing a browser. Prefer one browser-intensive lane; use more only when workers can share an existing runtime or cache without installing anything and their targets are independent. Do not download a new Playwright browser merely for screenshots without explicit need. If a source blocks one lane, try one credible alternative and then record the gap.

### 5. Capture source-faithful receipts

- Prefer primary and official sources for product claims.
- Preserve account, publication, date, headline, metric, and source branding needed to understand the receipt.
- Crop tightly enough for a phone screen without removing provenance.
- Time-stamp live social counters and mutable leaderboards.
- Save actual PNG data under `.png`; convert mislabeled JPEG screenshots before handoff.
- Never fabricate a tweet, article, benchmark, quote, price card, or UI to fill a blocked source.
- Treat official promo footage and third-party video excerpts as provenance-sensitive assets. Record the URL, owner, excerpt boundaries, and intended editorial use.

### 6. Route richer visuals selectively

When a beat would benefit materially from a diagram, coded animation, screen demonstration, generated still, or generated video, add it to a ranked visual-opportunity list and invoke `video-visual-assets-ops` for the chosen beats.

Do not let speculative animation delay the first usable screenshot pack. Deliver proof assets first, then upgrade the highest-value beats.

### 7. Verify the pack

Visually inspect every accepted image. Check:

- readable text at vertical-video scale
- no blank pages, consent overlays, accidental browser chrome, clipped headlines, or broken images
- correct file type and nonzero dimensions
- no conflicting live numbers across narration and screenshots without an editor note
- no test files or temporary profiles left in the asset folder

Probe both images and motion assets; do not infer media properties from a file
extension, editor thumbnail, or render settings. Run:

```bash
python3 scripts/inspect_asset_pack.py <assets-dir>
```

The inspector uses `ffprobe` for video metadata. Fix extension mismatches,
unusable crops, invalid duration or dimensions, and duplicate assets before
marking the pack ready. Record the probe output or its path in the manifest.

### 8. Write the editor manifest

Create `ASSET_MANIFEST.md` in the asset directory. Follow [manifest-schema.md](references/manifest-schema.md).

The manifest must include:

- numbered asset index with source URLs
- beat-by-beat placement, duration, and crop/motion guidance
- claim-safe wording and time-sensitive qualifiers
- unavailable assets and honest fallbacks
- a timed 45–60 second sequence when the video is short-form
- an optional richer-visual backlog that does not block the edit

## Output Contract

Return:

- project and asset-directory paths
- numbered, visually verified asset inventory
- `ASSET_MANIFEST.md`
- compatibility symlink or pointer status when imported media paths exist
- unavailable or blocked receipts
- generated/motion opportunities separated into `ready`, `local prototype possible`, and `approval required`
- exact next editor action

## Guardrails

- Do not disturb editor-imported folders or raw media.
- Do not present mutable rankings or counters as timeless facts.
- Do not use generic AI art as evidence for a real claim.
- Do not trigger billable image/video generation without approval.
- Do not copy private footage into public repositories.
- Do not hold the entire pack for one blocked asset; hand off the useful first pass and mark the gap.
- Do not own narration cleanup, speech EDLs, final exports, or public-script approval; compose the rough-cut, batch, and content workflows that own those decisions.
- Do not imply that asset gathering edits the CapCut timeline. Empty named draft creation may be composed through `weekly-video-batch-ops`; A-roll assembly, silence cuts, captions, pacing, and asset placement remain later editing work.
