---
name: social-hook-selection-ops
description: Select source-backed hooks for TikTok, Instagram Reels, and YouTube Shorts. Use for choosing or adapting opening lines, first frames, on-screen text, and retention angles.
memory_tags:
  - domain:social-media
  - workflow:hook-selection
  - skill_role:generator
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

Do not invent hooks from general taste when a promoted hook library or
performance-backed research source is available. Every recommended hook must
name the underlying hook family or pattern it came from. If no existing pattern
fits, say that the library lacks a good match, propose a new candidate pattern,
and keep it labeled `candidate` until validated.

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
5. Rank available hook patterns by evidence before writing lines:
   - owned-account `proven`
   - owned-account `proven-adjacent`
   - actual TikTok / Instagram / Shorts examples with performance evidence
     (`source-observed`)
   - unvalidated formulas or prompt-framework ideas (`candidate`)
6. Generate 3-5 candidate hooks from those ranked patterns.
   - Include the pattern name for each hook.
   - Include the source-strength label for each hook.
   - Keep the line easy to say on camera.
   - Preserve the user's intended thesis instead of simplifying away the
     controversial or specific part.
7. Pick one primary hook and one backup.

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
- are clever but hard to parse in the first 1-3 seconds
- flatten the user's specific thesis into a generic category claim
- cannot be traced to a named hook family, source-observed format, or explicit
  new candidate pattern

## Output Contract

Return:

```text
Best hook:
- Line:
- Source strength:
- Pattern:
- Source basis:
- Why it fits:
- First frame:
- On-screen text:
- Twist/payoff:

Backup:
- Line:
- Source strength:
- Pattern:
- Source basis:
- Why:

Avoid:
- [weak angle to skip]
```

If the user asks for many options, group them by source strength.

If the user asks why a hook was chosen, answer by pointing to the pattern,
source strength, and fit to the idea. Do not justify it only by saying it
"sounds viral."

## Updating A Hook Library

When the task includes documentation maintenance:

1. Keep source evidence in research/source files.
2. Keep reusable hook patterns in a promoted hook library.
3. Link the hook pattern back to source evidence.
4. Do not upgrade `source-observed` to `proven` until the user's own account
   validates it.

For a compact source-strength reference, see
`references/source-strength.md`.

For generic external hook formulas that can be adapted when no owned-account
pattern fits, see `references/external-hook-patterns.md`.
