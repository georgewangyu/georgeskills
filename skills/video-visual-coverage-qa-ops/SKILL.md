---
name: video-visual-coverage-qa-ops
description: Audit a first export, near-final render, or locked-A-roll video for visual coverage and overlay quality using its transcript or SRT, asset manifest, and optional read-only editor-metadata snapshot. Use after the A-roll/story is locked or when a user asks to evaluate B-roll, screenshots, overlays, visual pacing, caption collisions, evidence alignment, or unused prepared assets and wants exact timestamped fixes without mutating the live editor draft.
memory_tags:
  - domain:social-media
  - workflow:video-visual-coverage-qa
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:render
  - outputs:qa-report
  - risk:medium
---

# Video Visual Coverage QA Ops

Inspect what the audience actually sees after the spoken story is stable. Return a prioritized, timestamped repair list; do not silently edit the timeline or substitute automated taste for the creator's judgment.

## Input Gate

Resolve:

- one reviewable render or first export
- a time-aligned transcript or SRT when available
- the asset manifest or prepared asset directory when one exists
- target aspect ratio and caption-safe zones when known
- an optional copy or read-only snapshot of editor metadata
- the report or QA staging directory

Require the render for visual conclusions. Editor metadata alone is not proof of the rendered result. If no timed transcript exists, derive a temporary one when permitted or mark claim-to-visual alignment as lower confidence.

Treat locked A-roll as an upstream constraint. Do not reopen story selection, delivery, filler removal, or taste-sensitive silence cuts unless the user explicitly asks for that separate review.

## Safety Boundary

- Default to read-only inspection of renders, transcripts, manifests, and source assets.
- Never mutate a live CapCut draft. If metadata would help, close CapCut and inspect a backup or isolated snapshot, or proceed from the export only.
- Write only the QA report and optional temporary frame samples or contact sheets to a separate `qa/` or staging directory.
- Do not rename, move, overwrite, or re-encode source media as part of inspection.
- Treat A-roll-only intervals as editorial choices, not automatic failures.
- Recommend fixes; do not claim to automate story, pacing, comedic timing, or taste.

## Workflow

### 1. Build a timed evidence map

Segment the render by spoken beat and meaningful visual state. For each interval, record:

- start and end time
- spoken claim or emotional job
- visible treatment: A-roll, screenshot, article, table, UI, motion, logo, caption, or transition
- asset identity and provenance when known
- whether the visual proves, explains, decorates, or conflicts with the narration

Use the final render as ground truth for timing. Use editor metadata only to identify asset names, layer bounds, and planned placements that are not reliably recoverable from pixels.

### 2. Fan out larger reviews

Use available subagents proactively when the video is at least 45 seconds, contains eight or more prepared assets, or needs evidence, frame, and metadata review across separate inputs. Assign disjoint read-only lanes:

1. transcript-to-claim and evidence alignment
2. rendered-frame sampling, visual-change cadence, and caption collisions
3. manifest-to-timeline utilization and repeated-asset inventory
4. independent severity review and fix-order check

Give workers the same timebase and prohibit editor-draft mutation. The parent merges intervals, resolves conflicting timestamps against the render, and owns the final recommendations.

### 3. Measure coverage and failure candidates

Read [qa-rubric.md](references/qa-rubric.md) before scoring. Inspect at minimum:

- claim-bearing visual gaps
- screenshot and receipt hold duration
- unused prepared assets
- repeated static assets without a new crop, callout, or purpose
- dense tables, leaderboards, or UI without a focal callout
- caption collisions with faces, source labels, proof text, or safe zones
- evidence that is adjacent to, weaker than, or inconsistent with the spoken claim

Sample the hook densely, then every visual transition and every flagged interval. For motion, inspect the first, middle, and final frames. Do not infer legibility from filenames or timeline metadata.

### 4. Separate defects from taste notes

Classify each finding:

- `required`: factual mismatch, unreadable proof, misleading crop, severe collision, blank frame, or missing evidence for a claim presented as sourced
- `high leverage`: a likely comprehension or retention improvement with a clear fix
- `optional taste`: pacing, novelty, animation, or aesthetic refinement that could reasonably remain unchanged

Avoid turning every long A-roll span or static hold into a defect. Explain the audience cost and confidence for every non-required recommendation.

### 5. Write exact timed fixes

For every actionable finding, specify:

- current interval, to the nearest useful tenth of a second
- observed problem and frame evidence
- audience cost
- exact replacement, crop, highlight, motion, or duration change
- proposed in/out time and target duration
- asset to reuse, asset to acquire, or custom visual to create
- confidence and severity

Prefer a small ordered repair queue over a large generic idea list. Identify the first three changes that produce the largest comprehension or retention gain.

### 6. Compose asset workflows only after diagnosis

- Invoke `video-asset-pack-ops` when a required proof receipt is missing, an existing receipt is unusable, or the manifest needs a source-faithful replacement.
- Invoke `video-visual-assets-ops` only for selected high-value fixes that need a diagram, callout animation, screen demonstration, or other custom visual.
- Pass exact time ranges and narration sync points into those skills.
- Keep acquisition and production separate from this QA pass; rerun the rendered inspection after changes are exported.

## Output Contract

Return a `VISUAL_COVERAGE_QA.md` report, or the same structure in chat when no write location is authorized, containing:

1. render, transcript, manifest, and metadata inputs with confidence notes
2. total duration, intentional A-roll-only time, claim-bearing covered time, and flagged gap time
3. asset utilization: used, unused, repeated, and unidentifiable
4. timestamped findings ordered by `required`, `high leverage`, then `optional taste`
5. an exact repair queue with proposed in/out times and asset references
6. the top three changes to make before the next export
7. unresolved evidence or caption checks
8. a rerender-and-reinspect gate

If frame samples are retained, place them in the QA directory and link each finding to the relevant frame. Do not store private footage or extracted frames in a public skill repository.

## Guardrails

- Do not use change cadence alone as a quality score.
- Do not count captions as proof of an external claim.
- Do not fabricate missing evidence or infer that an unused asset must be inserted.
- Do not recommend motion merely to make the timeline busier.
- Do not obscure source attribution or change a receipt so aggressively that it becomes misleading.
- Do not call the edit complete until required findings are fixed or explicitly accepted by the creator.
