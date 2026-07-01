---
name: decision-gate-ops
description: Evaluate meaningful operational, automation, product, workflow, or personal execution decisions by surfacing constraints, tradeoffs, proof requirements, reversible defaults, and the principle to carry forward.
memory_tags:
  - domain:decision-making
  - workflow:decision-gate
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:decision-context
  - outputs:decision-brief
  - risk:medium
---

# Decision Gate Ops

## Trigger

Use when:
- the user asks whether to do something, automate something, commit to a workflow, or choose between options
- the decision has real tradeoffs, public/reputation risk, opportunity cost, or recurring workflow impact
- the user is stuck between "just automate it" and "keep manual control"
- another skill or workflow needs a decision-ready brief before acting

Do not use when:
- the choice is trivial and the user only needs a quick preference
- the user has not described enough context to identify the decision
- the work is already a pure implementation task with an approved plan

## Source Layers

If the workspace has `promptrepo/`, load relevant local layers before deciding:
- `promptrepo/decision-making/ray-dalio-principles/SKILL.md` for radical transparency, believability weighting, second-order consequences, and recurring patterns.
- `promptrepo/decision-making/ray-dalio-principles/prompts.md` when the user wants a reusable copy-paste prompt after the decision.

Use these influences directly:
- Matt Pocock-style grilling: ask one question at a time when the missing input materially changes the answer, and provide the recommended answer with the question.
- Matt Pocock-style decision mapping: if the decision has "fog of war" across multiple unknowns, create or recommend a compact decision map of research, prototype, and discuss tickets instead of pretending one session can resolve it.
- Peter Steinberger-style skill discipline: keep the decision brief operational, terse, and action-oriented; add helper scripts only after a repeated command or scoring workflow actually exists.

If the decision depends on whether an automation, integration, or agent workflow is proven, use `live-proof-gate-ops` for the proof threshold.

## Inputs

- Required: decision, options, current constraints, and why the decision matters now
- Optional: prior attempts, affected workflows, platform/API limitations, public/private risk, time budget, advisors, evidence, known failure modes

## Workflow

1. State the decision in one sentence.
2. Name the real constraint:
   - missing evidence
   - platform limitation
   - quality/taste risk
   - trust/proof gap
   - time or opportunity cost
   - reputational/public downside
   - maintenance burden
3. Classify the decision:
   - one-way door or two-way door
   - manual, assisted, semi-automated, or fully automated
   - taste-sensitive or mechanical
   - public-facing or private/internal
   - reversible experiment or durable operating rule
4. Identify the options, including the boring middle option:
   - do nothing
   - manual
   - assistant prepares, human approves
   - bot acts only on proven cases
   - full automation
   - research/prototype before deciding
5. Apply the decision lenses:
   - Radical transparency: what is true, not comforting?
   - Believability: whose evidence or track record deserves weight here?
   - Second-order effects: what gets easier or worse after the first outcome?
   - Automation boundary: which parts are boring and reversible, and which parts need human taste, judgment, or public accountability?
   - Proof threshold: what live evidence would make the decision safe enough?
6. Recommend the smallest decision that preserves upside:
   - choose a reversible default when the downside is bounded
   - keep a human gate where quality, taste, privacy, or public posting risk is high
   - run a prototype when behavior cannot be reasoned about from docs
   - run research when facts may have changed or external rules matter
7. End with the future principle:
   - one durable rule the user can reuse next time
   - one trigger that would cause the rule to change

## Automation Boundary Rubric

For automation decisions, score each area as `low`, `medium`, or `high`:

- `reversibility`: can mistakes be undone cheaply?
- `public risk`: would a bad action be visible or reputationally costly?
- `taste sensitivity`: does the outcome depend on creative judgment?
- `platform fragility`: are APIs, scheduling, formats, or account state unreliable?
- `proof maturity`: has the workflow passed live proof on the real path?
- `maintenance load`: will the automation become another system to babysit?
- `leverage`: does automation remove a frequent bottleneck?

Default rule:

```text
Automate boring, reversible, high-leverage steps first.
Keep human approval for public, taste-sensitive, or platform-fragile steps until live proof repeatedly beats the manual workflow.
```

## Decision Map Escalation

Use a decision map when:
- the decision has more than three unresolved questions
- one answer changes the shape of later questions
- the work needs research, prototyping, or separate discussion before deciding
- multiple agents or sessions may work on the decision

Keep the map compact:

```markdown
## #1: <Question>

Blocked by: #<ticket-number> or None
Type: Research | Prototype | Discuss

### Question

<decision question>

### Answer

<resolved answer or blank>
```

Stop after creating the map unless the user asks to resolve a ticket immediately.

## Output Contract

Return:
- decision in one sentence
- real constraint
- decision class
- options considered
- recommendation
- why not the strongest alternative
- automation/manual boundary, if relevant
- proof threshold or next experiment
- second-order consequence to watch
- future principle

## Guardrails

- Do not hide uncertainty behind a confident recommendation.
- Do not make full automation the default just because it is technically possible.
- Do not keep manual work by default when the risk is low, reversible, and repetitive.
- Do not ask multiple grilling questions at once.
- Do not write private user-specific principles into this public skill; store private overlays in the private repo.
