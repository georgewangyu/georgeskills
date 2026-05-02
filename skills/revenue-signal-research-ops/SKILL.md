---
name: revenue-signal-research-ops
description: Estimate which apps or SaaS products are making meaningful revenue from public commercial signals. Use for money maps, not breakout-from-small-base analysis.
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
- the user wants small-team, under-the-radar, or narrow-scope products that appear to make disproportionate revenue

Do not use when:
- the goal is only to list competitors
- the goal is to choose a product wedge without first collecting evidence
- the main question is “what small or simple product broke out unexpectedly?”

## Inputs

- Required: product list, category, or niche
- Optional: platform, price range, target customer, time window, team-size ceiling, funding preference, revenue-density target, public-noise ceiling

## Research Modes

Choose the mode before browsing.

### Absolute Revenue Mode

Use when the user asks for the biggest revenue pools or market leaders.

Optimize for:
- total revenue, ARR, subscription revenue, or product revenue
- clean public evidence from filings, earnings, investor materials, or credible third-party estimates
- category-level monetization scale

This mode will usually surface large public companies and platform suites.

### Asymmetric Revenue Density Mode

Use when the user asks for:
- small team, high revenue
- under-the-radar apps or SaaS
- “low public noise, high monetization”
- revenue per employee
- indie, bootstrapped, founder-led, or niche products
- YouTube-like creator/business signal where the interesting thing is the ratio, not the absolute size

Optimize for:
- revenue per employee or ARR per employee
- paid traction despite low follower count, low press, low funding, or narrow product scope
- high pricing power in a specific workflow
- review volume, App Store rank, traffic, job posts, customer logos, payment volume hints, or founder/operator disclosures
- durable monetization signals over hype, launches, and vanity metrics

Default exclusions in this mode:
- public megacaps
- broad horizontal suites unless the specific product line is small or newly broken out
- companies where team size and revenue density cannot be bounded even roughly

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
3. In asymmetric revenue density mode, also collect public-noise and team-size proxies:
   - LinkedIn headcount, About page, founder/team pages, GitHub org activity, job postings
   - X/LinkedIn/YouTube follower counts when relevant
   - funding status and press footprint
   - founder interviews, Indie Hackers posts, podcasts, MicroConf talks, TinySeed/Acquire listings, App Store analytics, or credible operator writeups
4. Score each product on evidence strength and revenue density, not on certainty theater.
5. Separate:
   - observed facts
   - plausible inference
   - unknowns
6. Produce a ranked opportunity view with confidence levels.

## Output Contract

- ranked list of products or categories
- revenue-signal rationale per item
- mode used: `absolute revenue` or `asymmetric revenue density`
- for asymmetric mode: estimated team-size band, revenue-density proxy, public-noise proxy, and why the ratio looks interesting
- confidence label (`high`, `medium`, `low`)
- caveats about what cannot be verified

## Guardrails

- Never invent exact revenue numbers without a source.
- Treat third-party estimate tools as signals, not truth.
- Prefer ranges and confidence notes over fake precision.
- In asymmetric mode, do not rank large incumbents merely because they make more revenue.
- In asymmetric mode, label whether the apparent opportunity is `small-team cash machine`, `niche B2B workflow`, `consumer subscription app`, `marketplace/tooling layer`, or `unclear`.

If the user is looking for asymmetric winners relative to size, audience, age, or apparent simplicity, hand off to `breakout-signal-research-ops`.
