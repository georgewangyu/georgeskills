---
name: video-visual-director-ops
description: Direct and execute the visual pass after a short-form video's A-roll and spoken story are locked. Use when a creator has a versioned A-cut export and wants Codex to decide and produce A-roll punch-ins or reframes, proof assets, B-roll, captions, sound effects, transitions, trend-informed treatments, diagrams, and Remotion animation while preserving the locked story. Supports live Remotion Studio review, full-composite renders, transparent overlay tracks, and individual editor assets.
memory_tags:
  - domain:video
  - workflow:post-a-cut-visual-direction
  - skill_role:orchestrator
  - repo_boundary:tools
  - inputs:locked-a-cut
  - outputs:visual-edit-plan-and-render
  - risk:medium
---

# Video Visual Director Ops

Turn a locked A-cut into one coherent visual treatment instead of a pile of disconnected assets. Own the creative visual pass while leaving the creator's story selection and taste-sensitive speech cuts intact.

## Operating Boundary

Start only after the spoken story is locked enough to create a versioned export. The default boundary is:

- The creator owns the final A-cut, performance choices, silence/filler decisions, and story lock.
- This skill owns visual pacing, A-roll scale and framing treatments, proof placement, B-roll, captions and text emphasis, sound design cues, transitions, diagrams, animation, and decisions to leave a beat visually quiet.
- Do not reopen the spoken story unless the creator explicitly asks for A-cut recommendations. If a visual problem actually originates in the A-cut, flag it separately.
- Never mutate a live CapCut project while the creator is editing it. Work from a versioned export or a safe copy.

## Required Intake And Lock Gate

Collect or derive:

1. A versioned A-cut such as `a_cut_v03.mp4`.
2. A timed transcript or SRT aligned to that exact export.
3. The script, hook intent, and any non-negotiable claims.
4. Existing asset manifest, screenshots, source links, and brand references.
5. Target aspect ratio, resolution, frame rate, and maximum duration.
6. Optional trend reference, creator example, or desired energy.

Record the A-cut filename, byte size, duration, frame rate, and a SHA-256 fingerprint in the visual-edit plan. If the A-cut changes, stop rendering against stale timings, create a new version, and reconcile every timed treatment before continuing.

## Step 1: Establish The Visual Language

Before producing anything, write two to four rules for the video. Examples include proof-first receipts, restrained punch-ins, one recurring highlight color, or animation only for mechanisms that cannot be explained by a screenshot.

Also set a density ceiling. A useful default for talking-head shorts is one meaningful visual change every two to four seconds, with intentional uninterrupted eye-contact beats. Do not add movement merely to satisfy the cadence.

## Step 2: Scout Trend Mechanics When Useful

Invoke `broad-video-trend-radar-ops` and/or `video-breakout-research-ops` when the creator asks for current editing references, names a trending format, or the treatment needs a fresh pattern interrupt. Have a dedicated trend-mechanics scout deconstruct the reference rather than return only links.

Read [trend-mechanics-brief.md](references/trend-mechanics-brief.md) for the required analysis. Borrow portable mechanics, not the exact style or identity of a living creator. Prefer evidence of repeated performance across several posts or creators over a single unexplained hit.

## Step 3: Build The Timed Beat Map

Map every meaningful transcript beat to exactly one primary visual job:

- preserve eye contact with A-roll only
- emphasize delivery with an A-roll punch-in, crop, reframe, or subtle move
- prove a claim with a source-faithful receipt
- clarify context with B-roll
- compress a concept with text or captions
- explain a mechanism with a diagram or motion sequence
- punctuate a transition with sound or a restrained visual reset

Use [edit-plan-schema.md](references/edit-plan-schema.md). For each beat, record exact in/out times, rationale, source or asset, execution mode, confidence, and whether the treatment is required evidence or optional taste.

The visual director decides what *not* to cover. Preserve the face when emotion, credibility, humor, or delivery is the main event.

## Step 4: Fan Out Production

For videos longer than 45 seconds, six or more meaningful beats, or three or more independent production lanes, use subagents proactively. Give each worker disjoint output paths and one bounded responsibility:

- `visual-trend-scout`: current references and portable edit mechanics
- `visual-beat-mapper`: transcript-to-treatment map
- `a-roll-treatment-worker`: punch-ins, reframes, scale rhythm, and face-safe crops
- `proof-and-broll-worker`: source receipts, B-roll, provenance, and legibility
- `remotion-sequence-worker`: one or more named motion sequences
- `visual-qa-worker`: independent render inspection against the plan

The parent owns the timebase, art direction, file naming, integration, and final judgment. Do not let separate workers invent conflicting visual systems.

Compose existing skills:

- Invoke `video-asset-pack-ops` for sourced screenshots, official receipts, and the numbered asset manifest.
- Invoke `video-visual-assets-ops` for selected diagrams, coded motion, screen demonstrations, generated media, or promo excerpts.
- Invoke `social-motion-diagram-ops` for Excalidraw-style diagrams when that visual grammar fits.
- Invoke `video-visual-coverage-qa-ops` after a reviewable render.

## Step 5: Choose The Execution Mode

Select the lightest mode that satisfies the plan:

1. **Full composite:** Use when the treatment changes A-roll scale, crop, position, timing, background, or layering. Render the A-cut and all overlays together.
2. **Transparent overlay track:** Use when the creator wants the A-roll untouched in CapCut or another editor. Render alpha video for overlays only. This mode cannot perform A-roll punch-ins or reframes.
3. **Individual editor assets:** Use when the creator wants manual placement or only a few custom sequences. Return editor-safe clips, stills, and exact timecodes.
4. **Live timeline integration:** Use Premiere or another editor bridge only when it has been separately configured and audited. Work on a duplicate sequence and dedicated tracks with an explicit apply gate. It is not the default path.

Read [remotion-handoff.md](references/remotion-handoff.md) before executing the default Remotion workflow.

## Step 6: Run The Live Remotion Loop

Use the installed Remotion skill/plugin for implementation details and load only the relevant Remotion rule files for video, sequencing, sound, captions, or transparent output.

1. Scaffold or reuse a project-local Remotion composition.
2. Keep timed treatments data-driven from the visual-edit plan rather than scattering unexplained frame constants.
3. Start Remotion Studio and expose the browser preview while iterating when the runtime permits.
4. Validate first, middle, and final frames for every high-value sequence before a full render.
5. Render the selected delivery mode and preserve the command, composition name, and output path.

Do not claim that a live preview is running unless it is actually accessible. Do not silently trigger paid image or video generation; obtain approval first.

## Step 7: Verify And Iterate

Verify dimensions, duration, audio sync, frame rate, alpha behavior when relevant, missing media, and representative frame samples. Then invoke `video-visual-coverage-qa-ops` against the render, timed transcript, asset manifest, and visual-edit plan.

Fix required evidence, legibility, timing, and technical defects before optional polish. Re-render until required issues are resolved or explicitly accepted. Taste notes remain recommendations for the creator, not hidden mutations.

## Output Contract

Return:

- `VISUAL_DIRECTION.md` with the visual rules and creative rationale
- `visual-edit-plan.json` or an equivalently structured Markdown plan
- `TREND_MECHANICS.md` when trend research was used
- the exact A-cut identity and fingerprint used for timing
- Remotion source/project path and preview instructions
- full composite, transparent overlay, and/or individual assets requested
- render validation notes and the final visual-coverage QA report
- explicit manual handoff steps, unresolved blockers, and any A-cut observations kept outside the visual pass

The run is not complete merely because assets exist. It is complete when the locked A-cut has a coherent, inspectable visual treatment and a verified reviewable output or exact editor handoff.
