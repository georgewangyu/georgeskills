---
name: product-ignition-critique-ops
description: Critique a product idea before building by testing whether the pain is legible, the demo is newsworthy, the ignition event is plausible, and the post-spike capture loop can turn attention into durable demand.
memory_tags:
  - domain:product-strategy
  - workflow:ignition-critique
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:product-idea
  - outputs:launch-readiness-critique
  - risk:medium
---

# Product Ignition Critique Ops

## Trigger

Use when:
- the user has a product idea and asks whether it is launchable, viral, or worth building
- the user asks for an ignition event, launch hook, or post-viral capture plan
- the idea depends on social proof, network effects, creator distribution, Product Hunt, press, or community spread
- the user wants a sharp pre-build critique rather than encouragement

Do not use when:
- the user only needs implementation planning
- the product is private/internal and does not need public ignition
- the user has not yet named a target user or painful workflow

## Inputs

- Required: product idea, target user, problem/pain, intended distribution surface
- Optional: demo concept, creator assets, audience, competitor examples, waitlist or pricing plan, current prototype state

## Workflow

1. State the idea in one sentence.
2. Test pain legibility:
   - Can the target user understand the problem in 5 seconds?
   - Is the pain frequent, expensive, embarrassing, urgent, or status-relevant?
   - Does the pain show up in public complaints or workflow workarounds?
3. Test demo/newsworthiness:
   - Can the product produce a before/after moment?
   - Is there a visual, numerical, or emotional proof event?
   - Would a creator, community, or journalist know how to explain it?
4. Name the ignition event:
   - specific launch surface
   - reason people arrive at once
   - borrowed audience or institution
   - initial proof artifact
   - fallback if the event does not happen
5. Define the capture loop:
   - CTA after attention
   - waitlist, demo request, signup, paid checkout, community, or teardown submission
   - follow-up sequence
   - evidence collected from early users
6. Plan for the trough after the spike:
   - retention diagnostic
   - activation bottleneck
   - next narrower re-ignition event
   - product iteration or customer-conversation loop
7. Decide:
   - build now
   - sharpen pain first
   - make demo first
   - find better ignition surface
   - downrank the idea

## Output Contract

Return:
- one-sentence product idea
- pain-legibility score
- demo/newsworthiness score
- ignition-event hypothesis
- capture-loop plan
- trough plan
- biggest risk
- recommended next experiment
- build/downrank recommendation

## Boundaries

- Be direct. Do not flatter weak ideas.
- Do not treat generic consistency as an ignition event.
- Do not confuse broad attention with qualified demand.
- Keep examples generic and public-safe.
