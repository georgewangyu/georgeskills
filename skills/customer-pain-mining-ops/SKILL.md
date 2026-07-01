---
name: customer-pain-mining-ops
description: Mine reviews and public discussions for repeated user pain points, unmet needs, and switching triggers.
memory_tags:
  - domain:market-research
  - workflow:pain-mining
  - skill_role:researcher
  - repo_boundary:tools
  - inputs:web
  - outputs:pain-point-map
  - risk:medium
---

# Customer Pain Mining Ops

## Trigger

Use when:
- the user wants unmet needs, complaints, and friction in a market
- the user asks what people dislike about existing apps or SaaS tools
- the goal is to identify openings for a better product wedge

Do not use when:
- the task is mostly competitor enumeration
- the task is mostly architecture or stack selection

## Inputs

- Required: product, niche, or category
- Optional: user type, platform, geography, price sensitivity

## Workflow

1. Browse current user-generated sources:
   - App Store reviews
   - Reddit
   - product forums
   - public support threads
   - social posts and comment sections
2. Extract repeated complaints, blocked workflows, and emotional language.
3. Group pain into buckets:
   - missing features
   - reliability
   - pricing resentment
   - onboarding confusion
   - trust/privacy concerns
   - poor support
4. Distinguish loud edge cases from repeated mainstream pain.
5. Note hints of willingness to pay, switching triggers, and underserved segments.

## Output Contract

- ranked pain-point list
- evidence snippets or source references
- pain frequency and severity judgment
- possible wedge implications

## Guardrails

- Do not overfit to a few angry comments.
- Prefer repeated pain across multiple sources.
- Separate “people complain a lot” from “people will pay to solve this.”
