---
name: personal-vision-interview-ops
description: Guide a private, one-question-at-a-time interview that helps a person clarify values, anti-vision, ordinary desired life, contribution, financial enough, time horizons, and unresolved questions, then synthesize the answers into a coherent personal VISION.md and decision gate. Use when someone wants to discover or revise a personal vision, turn reflection notes into a life-direction document, resume a paused vision interview, or give an AI durable guidance without inventing certainty.
metadata:
  memory_tags:
    - domain:personal-development
    - workflow:personal-vision-interview
    - skill_role:generator
    - repo_boundary:tools
    - inputs:reflection
    - outputs:vision-document
    - risk:medium
---

# Personal Vision Interview Ops

## Overview

Help a participant discover a vision rather than manufacture a polished life
story. Separate relatively stable direction from changing plans, preserve
unresolved questions, and make the final document useful for both the person
and agents acting on their behalf.

Read `references/interview-guide.md` before starting an interview or
synthesizing raw answers. Use `assets/VISION_TEMPLATE.md` as the output
scaffold, adapting it to the participant instead of forcing every section.

## Scope

Use this skill for a personal or family-level vision and its decision policy.
Do not use it to:

- diagnose mental-health conditions or replace professional care;
- choose legal, medical, or financial actions without the relevant specialist;
- turn an employer, product, or organization strategy into a personal vision;
- publish, share, or commit private answers without explicit approval;
- pressure a participant to disclose details or resolve uncertainty on demand.

## Inputs

Required:

- a participant willing to reflect, or notes/drafts they explicitly provide;
- the intended scope, such as whole life, career, family, or a transition.

Resolve during setup:

- mode: `interview`, `resume`, `synthesize`, or `revise`;
- desired depth: quick, standard, or deep;
- output behavior: chat draft only or a user-approved file path;
- privacy preference: what may be retained, quoted, generalized, or omitted;
- time horizon, if the participant already has one.

Optional:

- an existing vision, journal excerpt, decision log, or life-domain notes;
- current constraints, transitions, tensions, and known non-negotiables;
- intended consumers, such as the participant alone, family, coach, or AI.

## Workflow

### 1. Establish consent and boundaries

Explain that personal answers can include sensitive health, relationship,
identity, and financial information. Confirm the requested mode and privacy
preference before collecting substantive answers.

Default to a chat draft when no output path is approved. Never assume that a
file, repository, sync service, or shared workspace is private merely because
it is local.

### 2. Build a private working map

Track only what is needed to synthesize the vision. Classify working claims as:

- `confirmed`: the participant stated or approved it;
- `tentative`: a plausible interpretation to reflect back;
- `open`: intentionally unresolved or missing;
- `tension`: two desires or constraints that may conflict.

Do not present tentative interpretations as facts. Keep exact sensitive
figures and names only when the participant says they matter to the document.

### 3. Interview one question at a time

Follow the sequence in `references/interview-guide.md`. Start with values,
anti-vision, and an ordinary desired life before purpose, role, financial
enough, horizon ladders, or bespoke philosophical questions.

After each answer:

1. Mirror the useful meaning in one to three sentences.
2. Label any interpretation as tentative.
3. Ask at most one clarifying follow-up when the answer would materially
   change the vision.
4. Let the participant correct, skip, pause, or leave the question open.
5. Move to the next primary question only after acknowledging the answer.

Do not dump the full questionnaire into chat unless requested. Do not turn the
session into a quiz, assessment, or generic coaching monologue.

### 4. Adapt without losing the foundation

Use tailored follow-ups when an answer exposes a real ambiguity, identity
question, or conflict. Keep bespoke branches downstream of the core
foundation; an interesting philosophical detour must not crowd out ordinary
life, relationships, health, constraints, or near-term bridges.

For `synthesize` mode, map existing notes to the working categories first.
Ask only for gaps whose answers would materially change the document.

### 5. Separate direction from vehicles

Classify major commitments and goals as:

- `destination`: part of the life or contribution wanted for its own sake;
- `bridge`: builds freedom, capability, evidence, relationships, or capital
  needed for the destination;
- `experiment`: a bounded way to learn whether a direction fits;
- `proxy`: an indirect measure that can become detached from the real aim.

Name success traps: paths that look impressive or lucrative but would create
the wrong obligations, identity, environment, or opportunity cost if they
succeeded.

### 6. Draft without filling gaps

Synthesize the working map with `assets/VISION_TEMPLATE.md`. Prefer the
participant's own concrete language while avoiding long verbatim transcript
dumps. Include:

- a concise north star;
- an ordinary-life picture;
- values, non-negotiables, and an anti-vision;
- important questions or contribution domains;
- a current role hypothesis;
- destinations, bridges, experiments, proxies, and success traps;
- time horizons that the participant actually supplied;
- a decision gate for consequential choices;
- open questions and review triggers.

If a horizon or tradeoff is missing, mark it `Open` or omit it. Never invent a
one-year plan, financial target, relationship preference, or identity claim to
make the document look complete.

### 7. Run the confirmation pass

Present the draft as a proposal, then ask:

- What feels unmistakably true?
- What sounds polished but not actually yours?
- What important tension did the draft flatten?
- What is too private, too specific, or unnecessary to retain?
- Which open question should stay open?

Revise from the participant's corrections. Treat silence as neither approval
nor publication consent.

### 8. Save only to an approved boundary

Write a file only when the participant approved the path or clearly asked for
the file. If the target is public, shared, or has unknown visibility, stop and
offer one of:

- a private path selected by the participant;
- a redacted public version reviewed separately;
- a chat-only draft they can place themselves.

Never store interview transcripts, personal answers, or validation samples
inside this skill package.

## Output Contract

Return or create:

- a coherent personal vision document;
- explicit `Open` items rather than fabricated certainty;
- a short provenance note naming only the input types used;
- a review cadence or event-based review trigger;
- a decision gate that can guide the participant and authorized agents;
- a privacy receipt stating where the output was saved and whether anything
  was published or shared.

When a session pauses, return a compact private handoff containing completed
themes, open themes, the next question, and the approved storage boundary.

## Quality Checks

Before finalizing, verify:

- the participant can recognize their own language and priorities;
- the document describes an ordinary life, not only achievements;
- stable direction is separate from current tactics;
- health, relationships, autonomy, and other stated constraints are not
  silently traded away;
- every concrete horizon is supported by an answer;
- contradictions remain visible where they are not resolved;
- the decision gate can reject a plausible but misaligned opportunity;
- no private answer leaked into a public or skill-repository artifact.
