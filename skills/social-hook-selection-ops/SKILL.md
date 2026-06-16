---
name: social-hook-selection-ops
description: Select and adapt high-fit hooks for short-form social video ideas. Use when the user asks for a TikTok, Instagram Reels, YouTube Shorts, or short-form video hook; wants to choose between hooks; wants hooks based on proven, observed, or candidate patterns; or provides a video idea and asks for the strongest opening line, first frame, on-screen text, or retention angle.
memory_tags:
  - domain:social-media
  - workflow:hook-selection
  - outputs:recommendation
  - repo_boundary:tools
  - risk:low
---

# Social Hook Selection Ops

## Goal

Choose a small set of strong short-form video hooks from the best available
hook library, source research, and creator/account evidence, then recommend one
primary hook and one backup.

## Core Rule

Do not treat every good hook as equally proven.

Always label source strength:

- `proven`: worked on the user's own account or has strong owned-account
  precedent.
- `proven-adjacent`: close to the user's proven lane but not independently
  confirmed as a reusable winner.
- `source-observed`: observed from another creator/account with source notes
  and some performance evidence.
- `candidate`: plausible structure that still needs testing.

## Workflow

1. Identify the platform and objective:
   - TikTok, Instagram Reels, YouTube Shorts, or cross-posted short-form.
   - Reach, comments, saves, profile credibility, sponsor conversion, product
     conversion, or audience education.
2. Classify the video idea by proof type:
   - `life conflict`
   - `money/receipt`
   - `status/career`
   - `tool/demo/workflow`
   - `personal story`
   - `creator/process behind-the-scenes`
   - `utility/list`
   - `reaction/external spark`
3. Look for a local hook library in the active workspace before inventing from
   scratch. Common useful files are:
   - `hook-selection-workflow.md`
   - `viral-hooks.md`
   - `video/research/README.md`
   - account watchlists or dated hook research memos
4. Prefer promoted reusable hook libraries over dated research memos.
   - Use research memos to verify provenance or add a new pattern.
   - If a research memo has a useful pattern but the reusable hook library does
     not, promote the distilled pattern into the library when editing docs is
     part of the request.
5. Generate 3-5 candidate hooks:
   - start with `proven` and `proven-adjacent` patterns
   - add `source-observed` patterns when they fit the idea
   - use `candidate` patterns only when stronger sources do not fit
6. Pick one primary hook and one backup.

## Selection Heuristics

Prefer hooks that have:

- a visible first frame, not only a spoken sentence
- a concrete proof object: receipt, screenshot, demo, product, comment,
  calendar, bill, email, incident, before/after, or physical object
- tension by second 3
- a natural twist or payoff
- an audience that is broad at the start and specific after the click
- a body that can actually satisfy the promise

Avoid hooks that:

- are generic motivation
- require evidence the user does not have
- copy another creator's identity instead of borrowing the structure
- make claims stronger than the source supports
- start with topic labeling instead of tension

## Output Contract

Return:

```text
Best hook:
- Line:
- Source strength:
- Pattern:
- Why it fits:
- First frame:
- On-screen text:
- Twist/payoff:

Backup:
- Line:
- Source strength:
- Why:

Avoid:
- [weak angle to skip]
```

If the user asks for many options, group them by source strength.

## Updating A Hook Library

When the task includes documentation maintenance:

1. Keep source evidence in research/source files.
2. Keep reusable hook patterns in a promoted hook library.
3. Link the hook pattern back to source evidence.
4. Do not upgrade `source-observed` to `proven` until the user's own account
   validates it.

For a compact source-strength reference, see
`references/source-strength.md`.
