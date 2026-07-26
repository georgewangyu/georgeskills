---
name: shortform-talking-points-ops
description: Create natural point-form talking outlines and choose a minimal viable script structure for TikTok, Instagram Reels, and YouTube Shorts. Use when the user asks for beats, open loops, stakes, a climax, a twist, a hook-to-payoff structure, or help turning a short-form idea into a filmable outline. Do not use for raw-footage edit decisions or word-for-word scripts.
memory_tags:
  - domain:social-media
  - workflow:shortform-talking-points
  - skill_role:generator
  - repo_boundary:tools
  - outputs:talking-outline
  - risk:low
---

# Shortform Talking Points Ops

## Trigger

Use the frontmatter description as the trigger contract.

Route hook-only selection to `social-hook-selection-ops`. Route raw-footage
edit decisions to `shortform-rough-cut-ops`. If the user explicitly wants
word-for-word copy, use a full-script workflow instead.

## Inputs

- Required: short-form video idea, premise, or rough beats.
- Optional: target platform, duration, audience, hook evidence, core take,
  available proof, filming constraints, and desired ending.
- Infer safe missing details when possible; ask only when a missing fact would
  materially change the structure or claim.

## Core Rule

Default to a talking outline, not a full script.

For TikTok, Instagram Reels, and Shorts, a strong draft should help the creator
sound natural. Write enough structure to keep the take sharp, but leave room
for live phrasing, personality, pauses, and emphasis.

Treat an open loop as the unanswered question carrying the viewer forward. It
does not need to be a separate spoken line after every beat.

## Choose One Script Engine

### 1. Nested Escalation

```text
Hook -> Beat -> Open Loop -> Beat -> Open Loop -> Beat -> Twist
```

Use for chaotic stories, visible build stages, and situations that keep getting
worse or stranger. Carry several small questions rather than one long question.

### 2. Challenge Clock

```text
Question Hook -> Stakes / Rules -> Attempt -> Climax -> Result
```

Use for experiments, deadlines, and `Can I achieve X in Y time?` videos. Keep
one outcome question alive. Do not jump directly from stakes to climax; the
attempt is the evidence that earns the result.

### 3. Belief Reversal

```text
Familiar Belief -> Contradiction -> Proof -> Reframe
```

Use for hot takes, misconceptions, and `Everyone tells you X, but no one tells
you Y` ideas. The retention question is what the familiar explanation misses.

### 4. Confession / Hidden Cost

```text
Confession Hook -> Expected Reality -> Receipt -> Hidden Cost -> Reframe
```

Use for insider corrections and `Let's come clean about the reality of X`
ideas. Promise a concrete truth people normally omit.

### 5. Simple Model

```text
Confusing Question -> Simple Model -> Concrete Example -> Implication
```

Use for explainers where understanding is the payoff. Replace a confusing
mental model with a simpler one and prove it with one example.

Selection:

- Choose **Nested Escalation** when events progress through real complications.
- Choose **Challenge Clock** when the outcome and constraint are measurable.
- Choose **Belief Reversal** when the viewer should leave believing something
  different.
- Choose **Confession / Hidden Cost** when the value is an unspoken reality.
- Choose **Simple Model** when clarity itself is the payoff.

## Workflow

1. Define the viewer promise and central open loop.
   - Write the one question the viewer should still want answered.
   - Name the concrete payoff: result, reveal, reframe, or understanding.
2. Choose one script engine.
   - Use one dominant retention engine.
   - Add a midpoint rehook only when the next beat creates a real new question.
3. Select or verify the hook.
   - Use `social-hook-selection-ops` when hook quality matters.
   - Every hook should cite a source-strength label and named hook family when
     that information is available.
4. Identify the core take.
   - State the specific controversial claim in one sentence.
   - Preserve the user's real thesis; do not simplify away the hot part.
5. Draft only the beats the selected engine needs.
   - Label each beat by function, such as stakes, attempt, proof, complication,
     climax, result, or reframe.
   - Prefer one concrete receipt, demonstration, or before/after.
6. Make the take as sharp as the evidence allows.
   - Use direct language.
   - Name the villain, tradeoff, mistake, hidden cost, or false belief.
   - Add nuance after the hook, not before it.
7. Close the loop.
   - Use a result for a challenge, a reframe for a belief/confession structure,
     an implication for an explainer, or a twist for escalation.
   - Do not force a twist when the promised result is already satisfying.

## Output Contract

Return:

```text
Structure:
- Type:
- Formula:
- Why it fits:

Retention:
- Central open loop:
- Stakes or constraint:
- Promised payoff:

Hook:
- Spoken:
- On-screen:
- Source strength:
- Pattern:

Core take:
- [one sentence]

Minimal outline:
- [beat function]: [point-form beat]
- [beat function]: [point-form beat]
- [beat function]: [point-form beat]

Hot lines:
- [optional line]
- [optional line]

Ending:
- Climax/payoff:
- Twist/reframe/implication:

Caption:
- [platform-native caption]
```

## Guardrails

- Do not over-script unless explicitly asked.
- Do not make every sentence polished; leave natural speaking room.
- Do not make a bland educational outline when the user asked for a hot take.
- Do not mix multiple script engines unless the idea genuinely requires it.
- Do not add fake open loops or vague `wait for it` language.
- Do not add beats that do not raise stakes, provide proof, or close the loop.
- Do not invent performance evidence. Label unvalidated structures as
  `candidate`.
- Do not hard-code personal handles, private paths, or user-specific defaults.
