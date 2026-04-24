---
name: breakout-signal-research-ops
description: Find apps or SaaS tools with breakout traction relative to a small apparent starting base.
memory_tags:
  - domain:market-research
  - workflow:breakout-signal-detection
  - repo_boundary:tools
  - inputs:web
  - outputs:breakout-candidate-list
  - risk:medium
---

# Breakout Signal Research Ops

## Trigger

Use when:
- the user wants the SaaS or app equivalent of a low-follower viral breakout
- the task is finding unusually strong traction from a smaller, simpler, or newer product
- the user explicitly cares about asymmetry rather than absolute market leadership

Do not use when:
- the user only wants the biggest companies by revenue
- the task is broad category mapping without focusing on breakout candidates

## Inputs

- Required: category, niche, or platform
- Optional: age of product, team size, funding preference, target customer, geography

## Core Question

Ask:
- which products look small, new, niche, or simple
- but show disproportionately strong revenue, usage, growth, or attention anyway

This is the product equivalent of:
- low audience, one huge hit
- small team, outsized revenue
- narrow scope, surprising demand

## Workflow

1. Browse current sources and look for smaller or newer products in a category.
2. Collect breakout signals such as:
   - sharp App Store rank movement
   - unusually strong review growth
   - meaningful revenue despite small brand footprint
   - fast traffic growth from a narrow feature set
   - repeated mentions as a surprising newcomer
   - strong paid traction despite limited followers, funding, or surface area
3. Compare each candidate against its apparent starting base:
   - age
   - team size
   - funding
   - product breadth
   - audience size
4. Separate:
   - incumbents doing incumbent numbers
   - genuine breakout candidates
   - false positives driven by hype alone
5. Hand the strongest candidates to `customer-pain-mining-ops` and `idea-wedge-selection-ops`.

## Output Contract

- breakout candidate list
- why each candidate looks asymmetric
- signal type (`revenue`, `growth`, `attention`, `conversion`, `retention proxy`)
- confidence and caveats
- what small wedge might explain the breakout

## Guardrails

- Do not mistake press coverage for traction.
- Do not confuse downloads, followers, or traffic with monetization.
- Prefer products whose traction looks disproportionate to their apparent size.
- Explicitly call out when the breakout might just be temporary hype.
