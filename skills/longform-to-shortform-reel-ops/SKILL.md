---
name: longform-to-shortform-reel-ops
description: Select, score, and source-remap standalone vertical short-form clips from a finished long-form video, creator-edited timeline, transcript, and original camera/audio/screen-recording sources. Use when repurposing a course, podcast, interview, tutorial, livestream, or horizontal A-roll edit into Instagram Reels, TikTok videos, or YouTube Shorts; when the user wants a ranked candidate list before editing; or when an approved long-form cut must be traced back to higher-quality untouched media for vertical reframing.
memory_tags:
  - domain:social-media
  - workflow:longform-to-shortform
  - skill_role:operator
  - repo_boundary:tools
  - inputs:longform-video
  - outputs:reel-candidate-register
  - risk:medium
---

# Long-Form to Short-Form Reel Ops

Turn a finished long-form story into reviewable short-form candidates without
mistaking the baked export for the best production source. Use the final edit
to understand what survived; use original footage, isolated audio, screen
recordings, and editable motion sources to build approved reels later.

## Required Inputs

- A finished edit, review export, or read-only editor draft that exposes the
  creator's selected story.
- A timed transcript or a safe way to generate one.
- Original camera clips and audio when available.
- Screen recordings, proof assets, and editable animation sources when
  available.
- Target platform, target candidate count, and desired runtime range.

Treat `25-75s` as a useful candidate window for educational talking-head reels
when the user has not provided a stronger format rule. Do not force a complete
idea into that window when it needs more or less time.

## Source Hierarchy

Use each source for the job it is best at:

1. Use the finished edit or creator-edited draft as the editorial map.
2. Use its timed transcript and segment graph to identify exact surviving
   phrases, sequence, and pauses.
3. Remap approved ranges to untouched camera media for maximum crop latitude.
4. Use isolated recorder audio as the audio master when synchronization and
   quality are verified.
5. Use original screen recordings for legible proof crops.
6. Recompose editable Remotion, Manim, or design sources for `1080x1920`.
7. Use a baked long-form export only as a fallback when the original source
   mapping is missing or the baked treatment is itself the intended artifact.

Never overwrite, rename, or patch a creator source while selecting candidates.

## Workflow

### 1. Freeze the review surfaces

- Identify the untouched creator draft, the latest finished draft or export,
  and every available raw-source root.
- Record duration, frame rate, resolution, timeline version, and whether each
  surface has already been opened or edited.
- Keep the review read-only. Candidate selection does not authorize timeline
  mutation.

### 2. Build the transcript map

- Transcribe or load the complete creator-edited timeline.
- Preserve global finished-timeline timecodes.
- Identify section boundaries, repeated explanations, cautions, corrections,
  private disclosures, and claims needing evidence.
- When a segment map exists, retain segment id, finished-timeline range,
  source-media path, and source-media range.

### 3. Generate atomic reel candidates

- Make each candidate understandable without the long-form intro.
- Prefer one tension, mechanism, mistake, lesson, comparison, or demonstration
  per reel.
- Require a hookable first thought, enough setup to orient a new viewer, and a
  payoff or reframe.
- Allow a candidate to combine adjacent ranges when the joins remain truthful
  and natural. Expose every proposed join.
- Reject arbitrary equal-length chunks and fragments that depend on unseen
  context.

### 4. Score before ranking

Read [candidate-scale.md](references/candidate-scale.md) and score every
candidate out of 100. Apply risk deductions after the positive score. Keep the
component scores visible so the ranking can be challenged.

Default bands:

- `85-100`: A — edit first.
- `75-84`: B — strong candidate.
- `65-74`: C — usable with a better hook, proof asset, or tighter structure.
- `<65`: hold unless it serves a strategic series need.

Do not inflate scores to fill the requested count. Return weaker candidates at
the bottom with the actual weaknesses named.

### 5. Remap to original sources

- Match by exact phrase anchors plus timeline segment ids, not timestamps
  alone.
- Convert finished-timeline in/out points through the editor segment map to the
  original media in/out points.
- Verify the mapped words and picture at both boundaries.
- Prefer the original 4K camera clip for full-height vertical crops.
- Prefer the isolated audio file only after duration, waveform, and sync match.
- Note when a candidate crosses raw files or depends on a creator jump cut.
- Record the finished-to-master, master-to-camera, and master-to-audio stages
  with the controlled statuses and evidence rules in
  [candidate-scale.md](references/candidate-scale.md).
- Mark any candidate that cannot be remapped deterministically as
  `unavailable`; do not soften that state to imply it was verified.

### 6. Assign a vertical treatment

Read [vertical-layout-grammar.md](references/vertical-layout-grammar.md). Choose
only the modes the narration earns:

- `FACE`: full-frame tracked vertical A-roll crop.
- `SPLIT`: proof or example above, speaker below.
- `TAKEOVER`: short full-screen proof or meaningful multi-state animation.
- `QUIET`: uninterrupted A-roll for credibility, humor, or the payoff.

Do not shrink an entire desktop or a `16:9` animation into the vertical frame.
Crop the relevant UI region and rebuild motion graphics natively for `9:16`.
Borrow portable mechanics from references without copying another creator's
identity, branding, catchphrases, or complete edit style.

### 7. Return candidates before editing

Use [reel-candidate-register.md](assets/reel-candidate-register.md) as the
output shape. For each candidate include:

- rank and score band;
- proposed title and hook phrase;
- finished-timeline in/out and estimated cleaned runtime;
- one-sentence promise and payoff;
- finished-timeline-to-source-master mapping status;
- source-master-to-original-camera/audio mapping status;
- screen recording, proof, Remotion, or Manim opportunity;
- recommended vertical modes;
- required trims or joins;
- factual, privacy, or dependency risks;
- confidence and the reason it belongs at that rank.

Stop after the candidate register when the user asks to review ideas before
editing. Do not create CapCut drafts, render reels, rewrite hooks, or apply cuts
until the user selects candidates or separately authorizes production.

After approval, do not begin production unless original camera is `verified`
and original audio is either `verified` or `not-applicable`, or the user
explicitly authorizes a documented `finished-master exception` after seeing
the crop, audio, and quality limits. An approved idea is not approval to use
an unverified source.

Never label a flattened long-form master as `raw` merely because it is the
media referenced by the finished draft. Report the two conform stages
separately. A precise finished-timeline-to-master map does not prove a precise
master-to-camera/WAV map.

## Selection Rules

- Prefer source-faithful hooks over exaggerated creator copy.
- Treat the creator's finished long-form cut as evidence of preference, not an
  instruction to preserve every pause or sentence in short form.
- Reward real proof and demonstrable mechanisms; do not manufacture metrics.
- Preserve human presence. Visual coverage is not a reason to hide the speaker
  continuously.
- Separate a strong idea with weak delivery from a weak idea with polished
  visuals. Score both honestly.
- Flag corrections rather than reinforcing a spoken mistake with animation.
- Exclude credentials, private workplaces, homes, messages, tabs, tokens, and
  other sensitive material unless it has been explicitly cleared.

## Handoff After Approval

For selected candidates, create a new project-local reel packet containing:

- approved finished-timeline ranges;
- verified original camera and audio ranges, with evidence anchors;
- speech EDL and join notes;
- vertical layout beat map;
- proof and animation source paths;
- caption-safe zones;
- deterministic draft and asset names;
- validation status.

Use a separate new versioned editor draft for every later mutation batch.
Selection approval is not publication approval.
