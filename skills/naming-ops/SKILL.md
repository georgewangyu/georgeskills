---
name: naming-ops
description: Generate and screen brandable company, product, and SaaS names with domain and trademark checks.
memory_tags:
  - domain:naming
  - workflow:brand-naming
  - repo_boundary:tools
  - inputs:brand-brief
  - outputs:name-shortlist
  - risk:medium
---

# Naming Ops

## Trigger

Use this skill when the user wants help with:
- naming a company, startup, product, feature, or SaaS app
- moving from instinctive naming to a repeatable naming process
- generating name candidates with rationale, not just vibes
- preliminary screening for domain posture or trademark collision risk

Do not use this skill for:
- logo or visual identity work
- final legal clearance or legal advice
- registrar purchasing or trademark filing execution

## Inputs

- Required: what is being named, target audience, category, constraints
- Optional: preferred tone, words to include or avoid, target TLDs, geographic scope, naming examples the user likes or dislikes

## Workflow

1. Build a naming brief before generating names.
   Capture what the name must signal, what it must avoid, where it will be used, and whether the user wants company-level or product-level breadth.
2. Choose the right naming lane.
   Prefer strong marks over descriptive ones. Good default lanes are arbitrary, suggestive, or coined names. See `references/preliminary-clearance.md` for the USPTO framing.
3. Generate in batches, not one giant list.
   Produce a few clear lanes such as:
   - arbitrary real-word names
   - suggestive names
   - coined or blended names
   - phrase-based or editorial names when the brand should feel more narrative
4. Score candidates for brandability.
   Evaluate each name on:
   - distinctiveness in the category
   - ease of saying, spelling, and hearing correctly
   - semantic depth or rootedness
   - room to expand beyond the current product
   - visual cleanliness and URL cleanliness
5. Run preliminary clearance.
   Use official sources and web search, not guesswork:
   - federal trademark screen in the USPTO Trademark Search system
   - state business and state trademark search where relevant
   - broad web/common-law search for live use in adjacent categories
   - domain posture check for the target TLDs and realistic fallback patterns
6. Deliver a shortlist with explicit risk framing.
   Separate candidates into:
   - strongest now
   - interesting but risky
   - discard

## Screening Rules

- Treat this as a first-pass screen only. Never present a name as legally clear.
- Reject names that are highly descriptive in-category unless the user explicitly wants an SEO-style or generic name.
- Penalize names that are hard to spell after hearing them once.
- Penalize names that need explanation before they sound credible.
- Favor names that can hold more meaning over time instead of names that fully explain the current product on day one.
- If the user cares about broad defensibility, prefer arbitrary, suggestive, or coined names over literal phrases.

## Script Surface

Use `scripts/build_naming_shortlist.py` when the user already has a raw list of candidates and needs a compact shortlist worksheet with:
- normalized slugs
- target domains to check
- search prompts for trademark and common-law screening

## Outputs

- a naming brief
- a grouped candidate list with rationale
- a shortlist with risk notes
- a preliminary screening worksheet when needed

## Boundaries

- Public specs live in `liferepo` where relevant.
- This skill only covers naming workflow and preliminary screening.
- Final legal clearance should be done by qualified trademark counsel before launch or filing.
