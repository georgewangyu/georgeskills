---
name: asymmetric-revenue-case-study-ops
description: Produce single-company case studies for small-team, under-the-radar, or narrow-scope products that appear to generate disproportionate revenue; focuses on paid workflow mechanics, ignition events, pricing power, and transferable wedges.
memory_tags:
  - domain:market-research
  - workflow:revenue-density-case-study
  - repo_boundary:tools
  - inputs:web
  - outputs:case-study
  - risk:high
---

# Asymmetric Revenue Case Study Ops

## Trigger

Use when:
- the user names a company/product and wants to understand why it may be unusually cash-dense
- the user asks for a BuiltWith/Gamma-style case study
- the goal is to find transferable startup mechanics from a specific product
- the user cares about small-team revenue density more than absolute market size

Do not use when:
- the user wants a broad market map
- the user wants a list of the biggest companies by revenue
- there is no product/company target yet

## Inputs

- Required: company or product name
- Optional: category, suspected revenue signal, team-size constraint, pricing page, founder interview, target user, comparable products

## Workflow

1. Establish what is known:
   - product category
   - target user
   - core paid workflow
   - public pricing
   - available team-size, funding, traffic, customer, or usage signals
2. Gather current public evidence from primary or near-primary sources:
   - website and pricing pages
   - docs, changelog, and integrations
   - founder interviews or podcasts
   - job posts and team pages
   - customer stories and testimonials
   - credible third-party traffic/revenue/team-size estimates
3. Analyze revenue-density mechanics:
   - why the workflow is paid
   - why the buyer has urgency or budget
   - pricing-power sources
   - distribution advantages
   - automation or operational leverage
   - why the product can stay small-team or low-noise
4. Identify the ignition event:
   - launch, viral demo, SEO wedge, platform shift, community spread, dataset advantage, founder audience, or enterprise channel
5. Analyze post-ignition capture:
   - onboarding
   - upgrade trigger
   - retention loop
   - expansion path
   - why novelty did or did not become durable demand
6. Extract transferable wedge ideas:
   - analogous users
   - adjacent workflows
   - narrower MVP surface
   - creator/content hook
   - first distribution test

## Output Contract

Return a case study with:
- concise company/product snapshot
- confidence-labeled public evidence
- revenue-density rationale
- paid workflow and buyer pain
- pricing-power mechanics
- ignition event hypothesis
- post-ignition capture loop
- weak points and unknowns
- transferable wedge ideas
- one recommended follow-up research question

## Boundaries

- Do not invent exact revenue, team size, or conversion metrics.
- Label inference separately from sourced fact.
- Prefer ranges and confidence levels over false precision.
- If evidence is weak, say so and downgrade the case.
- Use this after `revenue-signal-research-ops` when moving from a list of candidates into one company deep dive.
