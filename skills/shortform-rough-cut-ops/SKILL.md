---
name: shortform-rough-cut-ops
description: Turn messy short-form video clips, creator intent, and optional format runbooks into an inspectable edit decision list and rough draft plan for CapCut or similar editors.
metadata:
  memory_tags:
    - domain:social-media
    - workflow:shortform-rough-cut
    - skill_role:operator
    - repo_boundary:tools
    - inputs:local-media
    - outputs:edit-decision-list
    - risk:medium
---

# Shortform Rough Cut Ops

## Trigger

Use when:
- the user wants help turning raw short-form video clips into a rough cut
- clips may be filmed out of narrative order and need to be mapped to story function
- the user has a recurring video format, hook pattern, or editing runbook
- the output should be an edit decision list, rough timeline, or CapCut draft plan

Do not use when:
- the user only wants viral-format research; use `video-breakout-research-ops`
- the user only wants transcription or archiving of a finished video
- the user wants final taste decisions fully automated with no human review

## Inputs

- Required: local clip folder or clip manifest
- Required: intended story flow, even if rough
- Optional: format runbook, script, reference video, music track, beat markers,
  target duration, platform, editor/draft tool, and creator-specific video
  history root

## Core Principle

The edit follows the intended story, not filename order.

Raw short-form clips are often captured opportunistically: B-roll may belong earlier than it was filmed, A-roll may explain a previous moment, and the strongest ending may be buried in the middle of the folder. Treat chronological order as metadata, not truth.

## Workflow

0. Load relevant edit history.
   - When a creator-specific history root exists, invoke
     `video-edit-history-ops` before story selection.
   - Read promoted defaults, recurring failure modes, and only the detailed
     records relevant to this format, editor, or risk.
   - Add applicable checks to the project ledger without treating project-only
     notes as universal rules.
1. Establish the target format.
   - Ask for the intended hook, situation, progress beats, twist or ending, and target platform.
   - Capture target duration. For short-form talking/story formats, treat 55-70 seconds as a useful default window when the user has no stronger format-specific target.
   - If the user provides a recurring format runbook, read it before classifying clips.
   - If no runbook exists, create a temporary working structure from the user's rough description.
2. Inventory the source clips.
   - Capture path, filename, duration, orientation, resolution, audio presence, and visible timestamp metadata when available.
   - Create or request a contact sheet when visual selection matters.
   - Do not move, overwrite, or rename raw media unless explicitly asked.
3. Transcribe and tag clips.
   - Transcribe speech clips with available local tools.
   - Mark clips without useful speech as visual/B-roll candidates.
   - Preserve exact phrases that identify anchor moments, transitions, progress updates, jokes, or twists.
   - For voiceover or A-roll-driven edits, use a staged A-cut workflow:
     first choose the spoken story ranges for the hook, setup, progression
     beats, twist, and ending; then run a separate tightening pass for dead air,
     long silences, false starts, repeated takes, filler-only fragments,
     abandoned sentences, duplicate ideas, and weak tangents.
   - Treat narration cleanup as iterative: rough story selection first,
     cleanup second, compression third. Do not use B-roll, captions, effects,
     or music to hide an unresolved spoken story.
   - Do not speed narration up by default; only apply speed changes when the
     user asks for that style or a format runbook explicitly calls for it.
   - Keep the cleaned speech timeline as an edit decision list of source ranges
     and removed ranges, not only as a baked audio export, so captions, overlays,
     effects, and B-roll can be retimed to the final narration.
4. Classify by story function.
   Use categories such as:
   - hook / anchor
   - setup
   - A-roll explanation
   - progress update
   - B-roll / montage
   - proof / detail
   - twist / ending
   - uncertain
5. Build an edit decision list before drafting.
   - Sequence selected clips against the intended story flow.
   - Include rough trims, rationale, confidence, and alternatives.
   - Flag whether the planned sequence is likely under or over the target duration.
   - Prefer two options when ambiguity is real: story-forward and montage-forward.
   - When speech drives the edit, lock the cleaned voiceover/A-roll timeline
     first, then place B-roll bridges, captions, overlays, sound effects, and
     proof assets against that cleaned timeline.
   - Surface removed ranges and alternate takes before drafting when the
     narration decision is ambiguous.
6. Plan editor automation only after structure exists.
   - Use CapCut or another draft writer as the timeline assembly layer, not the editing brain.
   - Generate a draft only from selected clips and rough trims.
   - Keep final pacing, text, effects, comedic timing, and taste-heavy choices human-reviewed.
7. Close the learning loop after review.
   - When the creator gives feedback or a meaningful review candidate is
     accepted or rejected, invoke `video-edit-history-ops`.
   - Record the exact artifact, timestamps, creator feedback, failure analysis,
     and unresolved issues.
   - Promote a future default only when the creator explicitly requests it or
     multiple independently reviewed edits support it.

## Output Contract

Return:
- clip inventory summary
- transcript/tag table or pointer to it
- clip classification table
- edit decision list with rough timing and rationale
- cleaned speech / voiceover range list when narration drives the edit
- unresolved questions or weak clips
- draft generation command or next manual editor steps, when applicable
- pointer to the updated per-video history record after creator review

## Guardrails

- Do not dump every clip into a timeline unless the user explicitly asks for assembly-only import.
- Do not hard-code one creator's format into the skill. Put format-specific rules in reference runbooks.
- Do not assume a strong hook or twist exists just because the format expects one.
- Do not invent clip contents. If visual inspection or transcription is missing, mark the gap.
- Do not copy private footage into public repos.
- Do not store creator-specific history in this reusable skill repo.
- Do not infer an editor preset from a compressed render; capture exact native
  values from the creator or a verified draft.

## References

Open only when needed:
- format runbook structure: `references/format-runbooks.md`
