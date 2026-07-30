---
name: strategic-capacity-allocator
description: Interview a person about vision, constraints, evidence, and competing priorities, then produce an auditable sprint-capacity recommendation using confidence-adjusted utility scores, floors, caps, opportunity cost, and diminishing returns. Use when someone asks how to divide limited weekly, sprint, quarterly, or portfolio capacity across career, business, creative, learning, exploration, or other strategic lanes; when building a vision allocator or prioritization frontend; or when a weighted recommendation needs to remain inspectable rather than becoming an opaque ranking.
metadata:
  memory_tags:
    - domain:decision-making
    - workflow:capacity-allocation
    - skill_role:evaluator
    - repo_boundary:tools
    - inputs:vision-and-priorities
    - outputs:allocation-recommendation
    - risk:medium
---

# Strategic Capacity Allocator

Turn a vague “what should I focus on?” discussion into an evidence-backed
allocation for the next marginal block of capacity. Treat the result as a
decision aid and experiment plan, never as an objective truth about a life.

## Workflow

1. Establish the decision frame:
   - planning horizon and total capacity
   - enduring vision or desired direction
   - current chapter and near-term obligations
   - health, relationship, financial, ethical, and contractual constraints
2. Define three to seven mutually legible lanes. Use outcomes or work systems,
   not a mixture of projects, identities, and vague aspirations.
3. Read [references/interview-guide.md](references/interview-guide.md) and
   conduct the interview one question at a time. Give a recommended answer or
   interpretation when the user is unsure, then let them correct it.
4. Read [references/scoring-model.md](references/scoring-model.md). Score the
   value of the **next marginal block** of effort in each lane, not the total
   lifetime value of the lane.
5. Record evidence and uncertainty before assigning numbers. Distinguish facts,
   estimates, preferences, and hypotheses.
6. Add allocation floors for real commitments or protected exploration and
   caps where more effort would crowd out recovery, exceed available work, or
   hit diminishing returns.
7. Prepare JSON matching the scoring-model schema and run:

   ```bash
   python3 scripts/score_allocations.py <input.json> --format markdown
   ```

8. Challenge the result:
   - rerun plausible low and high cases for uncertain scores
   - identify which changed assumption would alter the recommendation
   - test whether one piece of evidence was counted in multiple factors
   - flag any lane that wins mathematically but violates a hard constraint
9. Return a decision brief, not only a table.

## Output Contract

Return:

- decision frame and capacity
- recommended allocation by lane
- the main reason each lane received or lost capacity
- hard floors, caps, dependencies, and non-negotiables
- the two assumptions with the most leverage over the result
- a small reversible experiment for the least-certain material allocation
- review date and evidence to collect before recalculating
- explicit human overrides and their reasons

Use score ranges in prose when evidence is weak even though the CLI requires a
single scenario per run. Run multiple scenarios instead of averaging away
important uncertainty.

## Productizing the Workflow

When designing an application or generalized intake experience, read
[references/frontend-contract.md](references/frontend-contract.md). Keep raw
answers, evidence, derived scores, model configuration, and human overrides as
separate records so a recommendation can be audited or recalculated.

## Guardrails

- Do not outsource the user's values or final decision to the formula.
- Do not optimize through health, safety, integrity, family, or other declared
  hard constraints.
- Do not claim the default weights are scientifically estimated. They are
  transparent starting preferences.
- Do not compare lanes with different time horizons without naming the mismatch.
- Do not score entire careers when allocating one sprint. Score the next block.
- Do not let confidence become a bonus; use it only to shrink uncertain claims.
- Do not use opportunity cost as a second inverse-quality score.
- Do not count the same future asset, income stream, or credential twice.
- Do not force allocations below a real commitment or above a practical cap.
- Preserve an explicit exploration floor when uncertainty is strategically
  valuable and affordable.
