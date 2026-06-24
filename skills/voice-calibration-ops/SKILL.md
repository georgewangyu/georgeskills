---
name: voice-calibration-ops
description: Build or apply a source-derived writing voice profile from real samples, then draft or revise social posts, essays, emails, launch notes, and other prose so the output matches the supplied voice instead of generic AI style. Use when the user says text sounds off, generic, ungenuine, too AI-written, not in their tone, or asks to analyze past writing and write in that style.
memory_tags:
  - domain:writing
  - workflow:voice-calibration
  - inputs:writing-samples
  - outputs:voice-profile
  - repo_boundary:tools
  - risk:medium
---

# Voice Calibration Ops

## Goal

Turn real writing samples into an operational voice profile, then use that
profile to draft or revise prose. The output should sound like the source
writer's actual patterns, not like a generic platform post with a few banned
phrases removed.

## Inputs

Required:

- A target draft to revise, or a topic/brief to draft from.
- Either writing samples, links/files to inspect, or an existing voice profile.

Optional:

- Channel: X, LinkedIn, email, blog, docs, README, launch note, or internal
  memo.
- Desired stance: more casual, more direct, more technical, warmer, sharper,
  shorter, or more explanatory.
- Save location for a durable voice profile.

## Source Rules

Prefer source material in this order:

1. Recent original posts, essays, emails, launch notes, or memos from the
   target writer.
2. Finished pieces the user explicitly says "this sounds like me."
3. Drafts with user corrections that reveal what they reject.
4. Product docs or site copy only when the target voice is an organization or
   project, not a person.

Use 5-20 samples when possible. If fewer than three samples are available,
label confidence `low` and avoid strong claims about the voice.

Never store personal voice fingerprints in a public skill repo. If the user
wants persistence, write the profile to their private workspace or the path
they provide.

## Workflow

1. Identify the target channel and job:
   - `profile`: build a reusable voice profile.
   - `revise`: improve an existing draft.
   - `draft`: create new copy from a brief.
   - `audit`: flag mismatch without rewriting.
2. Gather and read the available source samples.
3. Extract the voice using
   `references/voice-profile-schema.md`.
   - Separate public-post voice from private-working voice when they differ.
   - Preserve contradictions instead of averaging them into vague advice.
4. Decide the output structure before writing:
   - For social posts, generate 2-3 hook angles before the body.
   - For essays or posts longer than 500 words, propose the structure first
     unless the user already gave one.
   - For quick rewrites, skip the structure proposal and edit directly.
5. Draft or revise using the profile.
   - Keep the writer's preferred rhythm, claim style, and compression.
   - Preserve the original factual claims unless the user asks for a rewrite of
     the argument itself.
   - Replace generic platform voice with source-backed phrasing.
6. Run the anti-generic pass in
   `references/anti-generic-writing-checklist.md`.
7. Return the final copy plus a short calibration note.

## Revision Heuristics

When a sentence feels off, diagnose the failure before rewriting it:

- `fake excitement`: launch-post enthusiasm without a concrete reason.
- `corporate filler`: words that flatter the work instead of explaining it.
- `platform cosplay`: LinkedIn/X cadence that could belong to anyone.
- `wrong intimacy`: too personal, too distant, too polished, or too casual for
  the source samples.
- `unsupported swagger`: confidence stronger than the evidence.
- `style graft`: one superficial trait copied while deeper rhythm stays generic.

Fix the cause, not only the sentence.

## Output Contract

For `profile` jobs, return:

```text
VOICE PROFILE
...
```

Use `references/voice-profile-schema.md`.

For `revise` jobs, return:

```text
Revised draft:
...

Calibration notes:
- What changed:
- Voice evidence:
- Remaining uncertainty:
```

For `draft` jobs, return:

```text
Voice profile used:
- Confidence:
- Source basis:

Hook options:
1.
2.
3.

Recommended draft:
...

Why this fits:
- ...
```

For `audit` jobs, return:

```text
Voice mismatch audit:
- Line:
- Issue:
- Why it misses:
- Suggested direction:
```

## Guardrails

- Do not imitate a writer the user is not authorized to write as for deception,
  impersonation, fraud, or undisclosed public representation.
- Do not claim perfect voice matching. Report confidence and uncertainty.
- Do not invent facts, credentials, personal history, private opinions, or
  emotional reactions to fill voice gaps.
- Do not overfit to quirks. A voice profile should capture reusable writing
  behavior, not turn the writer into a caricature.
- Do not use generic "AI detector" language as proof. Treat AI-writing signals
  as editing clues, not attribution evidence.
