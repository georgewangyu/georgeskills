---
name: rental-search-due-diligence-ops
description: Run bounded rental-search due diligence for apartments or homes by ranking candidates against commute, budget, amenities, reviews, exact-unit risks, tour questions, and stop conditions.
memory_tags:
  - domain:housing
  - workflow:rental-due-diligence
  - repo_boundary:tools
  - inputs:web
  - outputs:ranked-shortlist
  - risk:medium
---

# Rental Search Due Diligence Ops

## Trigger

Use when:
- the user is comparing rental apartments or homes
- the user asks for a ranked shortlist, tour checklist, or review-risk pass
- rental research is becoming open-ended and needs a bounded decision workflow
- the user has candidates and needs exact-unit due diligence before applying or signing

Do not use when:
- the user is buying property rather than renting
- the user needs legal advice about a lease
- there are no candidate properties, area, or must-have constraints yet

## Inputs

- Required: city/area, budget, commute anchor, must-haves, candidate list or search radius
- Optional: nice-to-haves, review threshold, building age preference, safety concerns, pet/parking/EV/AC needs, tour date, unit links

## Workflow

1. Confirm constraints:
   - budget and all-in cost assumptions
   - commute time and route type
   - must-haves and dealbreakers
   - preferred building feel and unit size
2. Build or clean the candidate set:
   - remove obvious mismatches
   - identify missing data
   - avoid expanding the search unless the current set fails
3. Score each candidate:
   - commute
   - price/value
   - exact-unit size/layout/light/noise
   - amenities that matter
   - review signal and complaint clusters
   - management/maintenance risk
   - block-level safety or access concerns
   - lease/application friction
4. Separate building-level and unit-level risk.
5. Write a tour or leasing-email script:
   - exact-unit questions
   - noise and construction questions
   - package/garage/access questions
   - utility, AC/heat, internet, and fee questions
   - move-in and concession details
6. Set a stop condition:
   - maximum number of candidates
   - next decision checkpoint
   - what evidence would make the top candidate signable

## Output Contract

Return:
- ranked shortlist
- reject/deprioritize list
- missing-data list
- exact-unit risk checklist
- review-risk summary
- tour/leasing questions
- recommended next action
- explicit stop condition

## Boundaries

- Do not give legal advice.
- Treat reviews as signal, not proof.
- Keep location examples generic; do not hardcode private addresses or personal defaults.
- Prefer bounded due diligence over endless candidate expansion.
