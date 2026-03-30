---
name: market-landscape-research-ops
description: Research a software or app market by identifying the main categories, leading products, pricing models, user segments, visible competitors, and smaller breakout upstarts. Use when comparing iPhone apps, SaaS websites, or adjacent product spaces before choosing what to build.
memory_tags:
  - domain:market-research
  - workflow:landscape-mapping
  - repo_boundary:tools
  - inputs:web
  - outputs:competitor-map
  - risk:medium
---

# Market Landscape Research Ops

## Trigger

Use when:
- the user wants to map a category before building
- the user asks which iPhone apps, SaaS products, or tools dominate a market
- the goal is to identify competitors, segments, and pricing patterns

Do not use when:
- the main goal is estimating who makes the most money
- the main goal is extracting customer pain from reviews and forums

## Inputs

- Required: category, niche, or product type
- Optional: platform (`iPhone`, `web SaaS`, `B2B`, `consumer`), geography, target customer

## Workflow

1. Browse current sources. Prefer official sites, app stores, pricing pages, rankings, and reputable market data.
2. Build a category map:
   - core use cases
   - target user types
   - top products by visibility
   - smaller or newer products with unusual traction
   - pricing patterns
   - product positioning differences
3. Separate direct competitors from adjacent substitutes.
4. Note where the market appears crowded, fragmented, or undersupplied.
5. Hand off promising categories to `breakout-signal-research-ops`, `revenue-signal-research-ops`, or `customer-pain-mining-ops`.

## Output Contract

- short category summary
- table or list of leading products
- pricing model notes
- direct vs adjacent competitor split
- explicit unknowns and next research step

## Guardrails

- Use dated sources because rankings and product leaders change.
- Do not infer revenue from visibility alone.
- Distinguish App Store popularity, web traffic, and brand awareness as different signals.
