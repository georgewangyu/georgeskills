---
name: revenue-signal-research-ops
description: Estimate which apps or SaaS products are likely making meaningful revenue by combining rankings, pricing, review volume, traffic, filings, hiring, and other public commercial signals. Use when the user wants a money map rather than just a competitor list.
memory_tags:
  - domain:market-research
  - workflow:revenue-signal-estimation
  - repo_boundary:tools
  - inputs:web
  - outputs:revenue-signal-sheet
  - risk:high
---

# Revenue Signal Research Ops

## Trigger

Use when:
- the user asks which products are generating the most revenue
- the goal is to prioritize markets based on monetization evidence
- the user wants a confidence-scored view of commercial traction

Do not use when:
- the goal is only to list competitors
- the goal is to choose a product wedge without first collecting evidence

## Inputs

- Required: product list, category, or niche
- Optional: platform, price range, target customer, time window

## Workflow

1. Browse current sources and prefer primary or near-primary evidence.
2. Collect public revenue signals, for example:
   - pricing pages and plan design
   - App Store ranking and review volume
   - traffic estimates and search demand
   - public filings, earnings, or investor materials
   - job postings that imply scale
   - funding, customer logos, and case studies
   - community evidence of paid usage
3. Score each product on evidence strength, not on certainty theater.
4. Separate:
   - observed facts
   - plausible inference
   - unknowns
5. Produce a ranked opportunity view with confidence levels.

## Output Contract

- ranked list of products or categories
- revenue-signal rationale per item
- confidence label (`high`, `medium`, `low`)
- caveats about what cannot be verified

## Guardrails

- Never invent exact revenue numbers without a source.
- Treat third-party estimate tools as signals, not truth.
- Prefer ranges and confidence notes over fake precision.
