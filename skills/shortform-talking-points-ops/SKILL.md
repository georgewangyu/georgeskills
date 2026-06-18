---
name: shortform-talking-points-ops
description: Create natural point-form talking outlines for TikTok, Instagram Reels, and YouTube Shorts using a sourced hook pattern, hot take beats, and a final twist. Use when drafting short-form talking-head videos, creator commentary, career takes, product takes, or opinion videos that should sound improvised rather than memorized.
memory_tags:
  - domain:social-media
  - workflow:shortform-talking-points
  - repo_boundary:tools
  - outputs:talking-outline
  - risk:low
---

# Shortform Talking Points Ops

## Trigger

Use when:
- the user wants an Instagram Reels, TikTok, or YouTube Shorts draft
- the user wants a video script that should sound natural on camera
- the user asks for point form, talking points, beats, a hook, or a twist
- the video is a short-form opinion, career take, creator take, product take,
  commentary, or educational talking-head post

Do not use when:
- the user wants an edit decision list from raw clips; use
  `shortform-rough-cut-ops`
- the user only wants hook selection; use `social-hook-selection-ops`
- the user explicitly asks for a fully written word-for-word script

## Core Rule

Default to a talking outline, not a full script.

For TikTok, Instagram Reels, and Shorts, a strong draft should help the creator
sound natural. Write enough structure to keep the take sharp, but leave room
for live phrasing, personality, pauses, and emphasis.

## Workflow

1. Select or verify the hook.
   - Use `social-hook-selection-ops` when hook quality matters.
   - Every hook should cite a source-strength label and named hook family when
     that information is available.
2. Identify the core take.
   - State the specific controversial claim in one sentence.
   - Preserve the user's real thesis; do not simplify away the hot part.
3. Draft in point form:
   - hook
   - context/setup
   - 3-7 talking beats
   - hot lines the creator can choose from
   - twist ending
   - optional caption
4. Make the take as sharp as the evidence allows.
   - Use direct language.
   - Name the villain, tradeoff, mistake, hidden cost, or false belief.
   - Add nuance after the hook, not before it.
5. End with a twist.
   - The twist should reframe the take, not merely summarize it.
   - Useful endings include: "the real question is...", "the trap is...",
     "the point is not X, it is Y", or "you are not doing A, you are doing B."

## Output Contract

Return:

```text
Hook:
- Spoken:
- On-screen:
- Source strength:
- Pattern:

Core take:
- [one sentence]

Talking points:
- [beat]
- [beat]
- [beat]

Hot lines:
- [optional line]
- [optional line]

Twist ending:
- [ending]

Caption:
- [platform-native caption]
```

## Guardrails

- Do not over-script unless explicitly asked.
- Do not make every sentence polished; leave natural speaking room.
- Do not make a bland educational outline when the user asked for a hot take.
- Do not invent performance evidence. Label unvalidated structures as
  `candidate`.
- Do not hard-code personal handles, private paths, or user-specific defaults.
