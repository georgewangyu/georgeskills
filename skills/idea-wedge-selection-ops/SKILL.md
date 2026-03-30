---
name: idea-wedge-selection-ops
description: Turn market, revenue, breakout, and pain research into a concrete product direction by selecting a sharp initial wedge, target user, and why-now thesis. Use when the user wants a shortlist of what not to build, what might work, and what to pursue first.
memory_tags:
  - domain:product-strategy
  - workflow:wedge-selection
  - repo_boundary:tools
  - inputs:research-findings
  - outputs:opportunity-shortlist
  - risk:medium
---

# Idea Wedge Selection Ops

## Trigger

Use when:
- market research has already produced competitors, revenue signals, breakout signals, or pain maps
- the user wants a concrete recommendation on what SaaS or app idea to pursue
- the task is narrowing broad opportunity into a focused starting wedge

Do not use when:
- the user still needs basic market mapping
- the task is choosing implementation architecture

## Inputs

- Required: findings from market, revenue, or pain research
- Optional: founder constraints, technical strengths, time budget, distribution advantages

## Workflow

1. Review the evidence and restate the candidate markets.
2. Score each opportunity on:
   - pain intensity
   - monetization evidence
   - asymmetry or breakout signal strength
   - crowding
   - founder advantage
   - speed to first usable product
3. Define a wedge in this form:
   - target user
   - painful moment
   - narrow promise
   - why this beats incumbents
4. Reject ideas that are broad, crowded, or weakly monetized.
5. Produce a short ranked set:
   - `do not pursue`
   - `possible`
   - `best current bet`

## Output Contract

- ranked shortlist
- one recommended wedge
- why-now thesis
- main risks and disqualifiers
- next validation step

## Guardrails

- Do not confuse “big market” with “good starting point.”
- Do not confuse “largest incumbent” with “best wedge.”
- Prefer one painful narrow workflow over a broad generic platform.
- Make the rejection reasons explicit.
