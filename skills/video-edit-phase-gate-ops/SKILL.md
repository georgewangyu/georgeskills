---
name: video-edit-phase-gate-ops
description: Orchestrate a short-form video edit through intake lock, narration/A-cut lock, asset and visual planning, editor assembly and persistence, rendered evaluation, and final acceptance. Use when starting or resuming a multi-step video edit, preparing a CapCut or similar editor handoff, handling sponsor/product footage or creator-supplied proof, recovering from repeated correction cycles, or requiring independent content, visual-brand, and technical-audio evaluator subagents before declaring an edit complete.
memory_tags:
  - domain:social-media
  - workflow:video-edit-phase-gate
  - skill_role:orchestrator
  - repo_boundary:tools
  - inputs:video-project
  - outputs:edit-gate-ledger
  - risk:medium
---

# Video Edit Phase Gate Ops

Keep one project ledger that says what is required, what changed, what has been
proved, and which exact render was evaluated. The parent video operator owns
the edit and the shared timebase. Evaluator subagents remain read-only and enter
at proof gates rather than acting as parallel editors.

## Initialize The Gate Ledger

Copy [video-edit-gates-template.md](assets/video-edit-gates-template.md) into the
active project as `VIDEO_EDIT_GATES.md`. Preserve prior decisions when resuming
an edit. Do not regenerate the file from memory or silently remove an accepted
requirement.

Keep this ledger thin. Store phase state, evidence paths and fingerprints,
exceptions, approvals, and evaluator verdicts. Link to the transcript, speech
EDL, text/SFX map, asset manifest, visual plan, editor handoff, and QA reports;
do not copy their full contents into a second checklist.

Use these states for each phase:

- `not_started`
- `in_progress`
- `blocked`
- `passed`
- `accepted_exception`
- `invalidated`

Record the current editor project, render, and upstream artifact fingerprints.
One clearly identified review candidate must exist at a time.

## Phase 0: Intake Lock

Before editing, record:

- every user request and supplied asset, with `required` or `optional` status
- intended beat, current assignment, and final disposition for each asset
- a pointer to canonical on-screen text covering exact copy, amount, reveal
  time, grouping, order, and safe-zone requirements
- a pointer to timed sound-design cues and requested music treatment
- a pointer to framing decisions for partial overlay, split frame, full-screen
  takeover, and intentional A-roll-only beats
- accepted discrepancies between narration, display copy, and evidence
- target duration, aspect ratio, resolution, frame rate, editor, and template
- delivery/editability target, including whether native editor tracks are
  required and which layers must remain independently editable
- exact named editor draft, project path or identifier, and version lineage
  when a native editor timeline is required

Do not pass while a required item is `unassigned` or an accepted discrepancy is
implicit. Use `video-asset-pack-ops` when required proof is missing.

## Phase 1: Narration And A-Cut Lock

Use `shortform-rough-cut-ops` or the invoking creator's A-cut runbook. Record:

- exact A-cut filename, duration, frame rate, byte size, and SHA-256
- aligned transcript or SRT identity
- selected and removed source ranges when the edit includes speech cleanup
- whether pauses are inherited, introduced, or awaiting creator judgment
- explicit creator approval or a documented creator-owned manual lock

Do not time downstream assets against an unlocked narration spine. An A-cut or
ripple-timing change invalidates every later timed phase.

## Phase 2: Asset And Visual Lock

Use `video-visual-director-ops` for the coherent treatment and
`video-visual-assets-ops` only for selected high-value assets. Require:

- a beat-to-treatment plan with exact in/out times
- a numbered asset manifest and provenance
- mapped face, caption, persistent-text, and platform safe zones
- semantic one-to-one text grouping; do not merge independent claims or rows
- a timed SFX cue map
- an explicit sound-design disposition: planned cues, intentional silence, or
  creator-approved dry edit; an empty cue map is not implicitly acceptable
- an explicit editorial reason for each full-screen takeover
- a motion job and state change for each full-screen takeover; reject static
  full-screen cards over talking-head A-roll
- a default budget of zero or one earned full-screen takeover for a
  talking-head short; document the separate comprehension or proof job for any
  additional takeover
- a synthetic-media classification; generated atmosphere or illustration must
  not be presented as product proof or source evidence
- probed technical metadata for every motion or video asset, including codec,
  dimensions, duration, frame rate, audio streams, and rotation when present

Run asset acceptance before timeline integration. For sponsor or product-demo
assets, inspect the first, middle, and final frames and verify correct product,
real product action, readable UI at playback size, acceptable orientation,
source integrity, and absence of unrelated creators or conflicting branding.
Reject filenames or source descriptions as proof of visible content.

## Phase 3: Assembly And Persistence

Treat the editor as the assembly layer, not the proof layer.

- Work on a named duplicate or versioned project.
- Back up and fingerprint the named source project. Prefer a uniquely named
  destination that does not already exist; it may be created and assembled
  while the editor is open on another project.
- Preserve a version-lineage manifest and project-local media references.
- Apply text, proof, visual, caption, and SFX timing against the locked A-cut.
- Record an assembly receipt for every planned SFX cue with asset, track,
  timestamp, gain, and expected audible job. Missing SFX tracks fail assembly
  unless the ledger explicitly records intentional silence or an approved dry
  edit.
- When native editor tracks are required, persist those layers in the declared
  editor project. External assets plus timecodes do not satisfy this gate.
- Reopen and resave the project when the editor format requires a persistence
  check.
- Verify synchronized project files or graph copies when the editor stores
  more than one canonical timeline representation.
- Surface that an externally created or changed draft may require a project-list
  refresh or editor restart before it appears.
- When mutating an existing draft that could be active in the editor, warn that
  concurrent saves may be last-writer-wins. Compare pre/post fingerprints and
  verify persistence; do not impose a blanket app-wide closure requirement.

Passing this phase proves that the draft persisted. It does not prove that the
audience sees or hears the intended result.

If the editor cannot be mutated safely, keep asset production moving in
parallel and create a unique versioned destination. If the native timeline
still cannot be written or verified, mark this phase `blocked`; do not
substitute an external composite for the requested editor deliverable.

## Phase 4: Rendered Evaluation

Export one review render from the exact current project version. Fingerprint
it and give every evaluator the same render, `VIDEO_EDIT_GATES.md`, transcript,
asset manifest, and safe-zone specification.

When the declared target is a native editor timeline, the review render must
come from that persisted editor version. A separately assembled composite may
be used as a visual prototype but cannot pass the persistence lane.

Read [evaluator-lanes.md](references/evaluator-lanes.md). Use three independent
read-only evaluator subagents when any mandatory trigger applies:

1. content and text
2. visual and brand
3. technical, audio, and persistence

Use `video-visual-coverage-qa-ops` inside the visual and brand lane. Add an
optional taste evaluator only when pacing, energy, novelty, or creative strength
needs a separate opinion. Taste findings remain optional unless they expose a
comprehension defect.

Each evaluator must return `PASS`, `FAIL`, or `BLOCKED`, exact evidence, and
findings classified as `required`, `high_leverage`, or `optional_taste`. The
parent may merge duplicate findings but may not silently override a required
failure.

The technical-audio lane must reconcile the cue-map count, assembled-cue
count, and audibly verified-cue count. It cannot return `PASS` from narration
continuity alone. Require a rendered-audio timestamp check for every planned
cue; mark masked, inaudible, mistimed, or speech-obscuring cues as failures.

## Phase 5: Final Acceptance

Fix required findings, export a new version, fingerprint it, and rerun the
affected lanes. Mark the edit accepted only when:

- every required ledger item has a visible or audible disposition
- all mandatory evaluator lanes pass or the creator explicitly accepts the
  documented exception
- the inspected render fingerprint matches the declared final candidate
- project persistence and media references are verified
- the final artifact matches the Phase 0 editability target
- unresolved taste notes are separated from defects
- the handoff identifies the final project, final render, remaining manual
  steps, and superseded versions

Write `VIDEO_EDIT_ACCEPTANCE.md` with the consolidated verdict. Do not call a
metadata-only change complete.

## Invalidation Rules

- A-cut replacement or ripple timing: invalidate phases 2–5.
- Text, amount, category, or supplied-asset requirement change: invalidate the
  affected plan, assembly, and all relevant evaluator lanes.
- Asset replacement: rerun asset acceptance and rendered visual-brand QA.
- Sound-cue or narration change: rerun technical-audio QA.
- Editor resave after the evaluated export: create and inspect a new render.
- Delivery/editability feedback: invalidate phases 2-5 when the accepted
  visual system or required editor surface changes.
- Accepted exception change: reopen every downstream decision that relied on
  it.

## Subagent Policy

Do not spawn an evaluator for every mechanical phase. The parent operator owns
intake, editing, integration, naming, timebase, and fixes. Use evaluator
subagents as independent verification surfaces with disjoint contracts and
read-only access. Do not leak the expected answer; pass the raw render and
requirements.

## Output Contract

Maintain or return:

- `VIDEO_EDIT_GATES.md`
- pointers and fingerprints for the speech EDL, A-cut, canonical text map,
  timed SFX cue map, asset manifest, visual plan, editor handoff, and render
- project/version lineage, persistence evidence, and accepted exceptions
- pointers to lane-specific evaluator reports and their verdicts
- `VIDEO_EDIT_ACCEPTANCE.md` tied to the final render fingerprint

The run is complete only when the rendered result, not merely the timeline,
satisfies every required gate or records an explicit creator exception.
