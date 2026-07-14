---
name: video-visual-director-ops
description: Direct and execute the visual pass after a short-form video's A-roll and spoken story are locked. Use when a creator has a versioned A-cut export and wants Codex to apply a creator visual-style profile and produce A-roll punch-ins or reframes, proof assets, B-roll, captions, sound effects, transitions, trend-informed treatments, diagrams, and Remotion animation while preserving the locked story. Supports live Remotion Studio review, full-composite renders, transparent overlay tracks, and individual editor assets.
---

# Video Visual Director Ops

Turn a locked A-cut into one coherent visual treatment instead of a pile of disconnected assets. Own the creative visual pass while leaving the creator's story selection and taste-sensitive speech cuts intact.

## Operating Boundary

Start only after the spoken story is locked enough to create a versioned export. The default boundary is:

- The creator owns the final A-cut, performance choices, silence/filler decisions, and story lock.
- This skill owns visual pacing, A-roll scale and framing treatments, proof placement, B-roll, captions and text emphasis, sound design cues, transitions, diagrams, animation, and decisions to leave a beat visually quiet.
- Do not reopen the spoken story unless the creator explicitly asks for A-cut recommendations. If a visual problem actually originates in the A-cut, flag it separately.
- Give every programmatic CapCut mutation batch a brand-new versioned draft.
  Never patch a draft after it has been opened in CapCut; treat it as an
  immutable source and duplicate it to the next version. CapCut may remain open
  while the new target is assembled, but the creator must not open that target
  until the complete graph and Media-panel indexes have been verified.

## Required Intake And Lock Gate

Collect or derive:

1. A versioned A-cut such as `a_cut_v03.mp4`.
2. A timed transcript or SRT aligned to that exact export.
3. The script, hook intent, and any non-negotiable claims.
4. Existing asset manifest, screenshots, source links, and brand references.
5. Target aspect ratio, resolution, frame rate, and maximum duration.
6. Optional trend reference, creator example, desired energy, and mechanic
   budget. Default to one borrowed mechanic for a short unless asked otherwise.
7. A creator visual-style profile when one exists. Record its path and version;
   keep creator-specific preferences outside this reusable skill.
8. The project's `VIDEO_EDIT_GATES.md` when the invoking workflow uses
   `video-edit-phase-gate-ops`, including required supplied assets, canonical
   text, sound cues, framing decisions, and accepted discrepancies.
9. The required delivery target: native editable editor timeline, editable
   asset bundle, transparent overlay, review composite, or final composite.
   Record which layers must remain editable before producing assets.
10. When the target is a native editor timeline, the exact named draft,
    project path or identifier, and version lineage. Do not let a generic
    `CapCut draft` label stand in for the project that must receive the work.

Record the A-cut filename, byte size, duration, frame rate, and a SHA-256 fingerprint in the visual-edit plan. If the A-cut changes, stop rendering against stale timings, create a new version, and reconcile every timed treatment before continuing.

Spot-check the supplied SRT against the fingerprinted export at the opening,
middle, and ending; do not trust a filename or "matching" label alone. Inventory
supplied assets before acquiring anything new. Number them, verify provenance,
rights, privacy, legibility, and claim fit, and invoke `video-asset-pack-ops` only
for missing, weak, or unusable proof.

Do not silently drop a required ledger item. Build an exact text map with copy,
amount, reveal time, grouping, order, and safe zone. Build a timed sound-design
cue map alongside the visual beat map; track presence is not proof that a cue is
audible in the rendered result.

Once the A-cut identity, named editor target, shared timebase, and disjoint
output paths are locked, start independent proof inventory, face-safe beat
mapping, text preparation, and motion-concept lanes immediately. Do not wait
for one lane to finish before starting another that does not depend on it.

## Step 1: Establish The Visual Language

Before producing anything, load the creator's visual-style profile when one
exists and resolve the project preset, fonts, colors, safe zones, approved
recipes, and exceptions. Read
[creator-style-profile.md](references/creator-style-profile.md) for the schema
and runtime rules. Then write two to four project rules for the video. Examples
include proof-first receipts, restrained punch-ins, one recurring highlight
color, or animation only for mechanisms that cannot be explained by a
screenshot.

Also set a density ceiling. A useful default for talking-head shorts is one meaningful visual change every two to four seconds, with intentional uninterrupted eye-contact beats. Do not add movement merely to satisfy the cadence.

## Step 2: Scout Trend Mechanics When Useful

Invoke `broad-video-trend-radar-ops` and/or `video-breakout-research-ops` when the creator asks for current editing references, names a trending format, or the treatment needs a fresh pattern interrupt. Have a dedicated trend-mechanics scout deconstruct the reference rather than return only links.

Read [trend-mechanics-brief.md](references/trend-mechanics-brief.md) for the required analysis. Honor the project's mechanic budget; the default is one portable mechanic, not a sampler of every observed technique. Borrow mechanics, not the exact style or identity of a living creator. Prefer evidence of repeated performance across several posts or creators over a single unexplained hit.

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

### Preserve the A-roll canvas

When the A-roll is the persistent authenticity layer, default proof images and
custom motion to partial-frame overlays that leave the speaker visible. A
full-screen takeover must have a specific editorial reason; it is not the
default merely because an asset was rendered at 9:16.

Before adding a generic floating card, inspect the footage for a motivated
in-scene proof surface such as a monitor, phone, poster, whiteboard, or empty
wall region. When perspective, legibility, and face safety allow, place the
source-faithful receipt or diagram into that surface and return it to the
original scene after the proof job. Treat this as a project-specific option,
not a universal template; do not cover meaningful background action or
misrepresent the inserted object as something captured in camera.

Do not use a static full-screen card over talking-head A-roll. A full-screen
takeover must either show legibility-critical product proof or contain a
meaningful multi-state motion sequence that advances the explanation. Keep it
as short as the visual job allows, then return to the speaker. A still or a
single looping scale move belongs in a partial-frame overlay.

Default to zero or one full-screen takeover in a talking-head short. Additional
takeovers each require a distinct comprehension or proof job; visual variety by
itself is not a reason.

Map persistent template text, captions, and face-safe zones before sizing
overlays. Inspect the assembled composite—not only the isolated asset—and
reject any placement that covers required text or the speaker's important
action.

Treat the creator's accepted title placement as a compositional anchor, not
only as a collision zone. When the established title stage is centered in the
lower third and the speaker remains readable, default explanatory overlays to
that same center-bottom stage at a legible presentation size. Use an off-axis
corner or shoulder placement only when it avoids the face/action or performs a
specific proof-comparison job. Before placing a batch, composite one
representative overlay over the real A-roll at delivery resolution and approve
its anchor, scale, and title relationship; propagate that approved geometry to
the remaining family.

Keep running-list text semantically one-to-one with the narration. Do not merge
independent categories or claims into one row merely to save space; add a row
and reflow the later items while preserving their reveal order.

Reject generic synthetic "AI interface" cards, fake product screens, and a
repeated stack of interchangeable paper panels. Use source-faithful UI and
receipts for proof. Generated media may create atmosphere, metaphor, or a
clearly illustrative transition, but it may not impersonate evidence.

## Step 4: Fan Out Production

For videos longer than 45 seconds, six or more meaningful beats, or three or more independent production lanes, use subagents proactively. Give each worker disjoint output paths and one bounded responsibility:

- `visual-trend-scout`: current references and portable edit mechanics
- `visual-beat-mapper`: transcript-to-treatment map
- `a-roll-treatment-worker`: punch-ins, reframes, scale rhythm, and face-safe crops
- `proof-and-broll-worker`: source receipts, B-roll, provenance, and legibility
- `remotion-sequence-worker`: one or more named motion sequences
- `visual-qa-worker`: independent render inspection against the plan

The parent owns the timebase, art direction, file naming, integration, and final judgment. Do not let separate workers invent conflicting visual systems.

Before integrating sponsor or product-demo footage, inspect its first, middle,
and final frames. Verify the correct product and real product action, readable
UI at playback size, suitable orientation, source integrity, and absence of an
unrelated creator, room, conflicting branding, or baked filler. Reject an asset
that is merely the correct file type or from the correct URL but fails the
visible product job.

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

When the creator says only that they want to finish in CapCut, default to a
**CapCut finishing bundle** instead of silently baking away editability. Return
a review composite, alpha overlays and/or individual assets, and
`CAPCUT_HANDOFF.md` with exact timecodes. Express A-roll punch-ins and reframes
as timecoded CapCut instructions. Ask once before baking those A-roll changes
into the only delivery, and state exactly which layers remain editable.

When the creator explicitly asks for the work to be **in CapCut**, the native
CapCut draft is a required deliverable. Separate files plus placement
instructions are not equivalent. Produce editor-safe assets in parallel, then
back up and fingerprint the source, create a brand-new versioned destination,
and assemble only that unopened destination. Never overwrite or return to a
same-name target. CapCut may remain open on another project; expose the new
version only after the mutation batch and media-index verification are complete.
Before any native CapCut mutation, read
[capcut-native-draft-safety.md](references/capcut-native-draft-safety.md) and
run its archetype preflight. Treat a compound/nested A-cut as source footage,
never as the structural template for a new overlay. Abort the batch when no
known-good ordinary overlay archetype is available; do not infer that the only
video segment in a draft is safe to clone.
After the first open/save, freeze that version against automation. Any further
bot pass duplicates it to the next version. Verify the opened version retained
its tracks and media references, synchronized graph copies agree, and the
review candidate was exported from that exact draft.
Every programmatically inserted project-local clip must also be registered in
CapCut's Media-panel indexes, with its own `local_material_id`; copying the
file and adding a timeline material is not sufficient. Verify that each local
clip's id is present in both `draft_meta_info.json` and
`draft_virtual_store.json`, and that the Media-panel import count increased as
expected. A timeline clip that plays but is absent from Media is an incomplete
integration. After the first CapCut save, read the graph and indexes back. If
CapCut removed an entry, stop; do not repair the opened version in place.
Recover into another new version. Use a full CapCut restart only as a fallback
when the new version is not discovered or a controlled first-open test shows
that the current session retained stale project metadata.

Keep the creator source draft and the latest verified bot version. After the
successor has opened, saved, and passed graph/media read-back, move superseded
bot versions to Trash. Never delete the source, the only verified version, or a
predecessor before successor verification.
If native mutation is unavailable, mark the editor delivery blocked and return
the prepared assets; do not call the external composite the finished CapCut
edit.

Read [remotion-handoff.md](references/remotion-handoff.md) before executing the default Remotion workflow.
Read [render-fast-path.md](references/render-fast-path.md) before selecting a
render pipeline or starting a full-duration render.

## Step 6: Run The Live Remotion Loop

Use the installed Remotion skill/plugin for implementation details and load only the relevant Remotion rule files for video, sequencing, sound, captions, or transparent output.

1. Reuse the configured shared Remotion runtime and dependency installation.
   Keep `node_modules` outside individual video folders; a video's
   `visual-pass/remotion/` may contain only project-specific source, data, and
   render configuration. If the shared runtime is unavailable, stop and report
   the blocker instead of silently creating a second installation.
2. Keep timed treatments data-driven from the visual-edit plan rather than scattering unexplained frame constants.
3. Start Remotion Studio and expose the browser preview while iterating when the runtime permits.
4. Run the render preflight and benchmark one representative `5-10s` sample.
   Reject a path whose projected duration is disproportionate to the edit.
5. Validate first, middle, and final frames for every high-value sequence before a full render.
6. Render the selected delivery mode and preserve the command, composition name, output path, elapsed time, and any failed attempts.

Do not claim that a live preview is running unless it is actually accessible. Do not silently trigger paid image or video generation; obtain approval first.

Route every visual job by what it must accomplish. Use source-faithful
screenshots, screen recordings, or official demo footage whenever the beat
proves a product or claim. For cinematic atmosphere, transformation shots,
metaphor, or clearly synthetic inserts, prefer the authenticated Gemini
consumer video surface when it is available and approved. Use coded Remotion
motion for precise explanatory or UI animation, diagrams, legible text,
deterministic timing, and reusable brand treatments. Keep Higgsfield parked
unless the user separately approves its paid subscription for a specific shot.
Preserve the provider, displayed model, prompt, billing surface, and synthetic
status in the asset manifest; never use generated product UI as proof.

Treat Blender MCP as a heavier, explicit opt-in 3D lane. Do not propose or use
it from a generic request for a fancy edit, cinematic B-roll, or animation.
Route to Blender only when the creator explicitly names Blender, Blender MCP,
or a bespoke 3D treatment; then compose `video-visual-assets-ops`, preserve the
editable `.blend` scene, render a short low-resolution proof before final
output, and keep the shot outside the critical path until it passes QA.

## Step 7: Verify And Iterate

Verify dimensions, duration, audio sync, frame rate, alpha behavior when relevant, missing media, and representative frame samples. Then invoke `video-visual-coverage-qa-ops` against the render, timed transcript, asset manifest, and visual-edit plan.

Run a sound-design coverage check against the rendered candidate, not only the
timeline. Reconcile every planned SFX cue to an audible timestamp and record
`implemented`, `intentionally silent`, `masked/inaudible`, or `missing`. A
non-empty visual transition plan with an empty SFX map fails unless the creator
explicitly chose a dry edit. Do not pass the visual run while any required cue
is missing or inaudible.

Fix required evidence, legibility, timing, and technical defects before optional polish. Re-render until required issues are resolved or explicitly accepted. Taste notes remain recommendations for the creator, not hidden mutations.

If the creator reports new silence after the visual pass, compare the assembled
narration segments and source ranges against the locked A-cut before editing
speech. If they are unchanged, report that the pauses are retained A-cut
material. Any accepted ripple deletion invalidates later visual, text, caption,
and SFX timing; never shorten only the audio layer and leave those tracks stale.

## Output Contract

Return:

- `VISUAL_DIRECTION.md` with the visual rules and creative rationale
- `visual-edit-plan.json` or an equivalently structured Markdown plan
- `TREND_MECHANICS.md` when trend research was used
- the exact A-cut identity and fingerprint used for timing
- Remotion source/project path and preview instructions
- full composite, transparent overlay, and/or individual assets requested
- `CAPCUT_HANDOFF.md` when the creator will finish in CapCut, including exact
  placement instructions and an editability inventory
- render validation notes and the final visual-coverage QA report
- canonical text and timed sound-design cue maps, plus updated phase-gate
  status when `VIDEO_EDIT_GATES.md` is present
- explicit manual handoff steps, unresolved blockers, and any A-cut observations kept outside the visual pass

The run is not complete merely because assets exist. It is complete when the locked A-cut has a coherent, inspectable visual treatment and a verified reviewable output or exact editor handoff.
