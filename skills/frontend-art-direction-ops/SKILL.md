---
name: frontend-art-direction-ops
description: "Build a clear visual direction for a UI or landing page before implementation: references, typography, color, layout, and motion."
memory_tags:
  - domain:frontend-design
  - workflow:art-direction
  - skill_role:generator
  - repo_boundary:tools
  - inputs:product-brief
  - outputs:visual-spec
  - risk:medium
---

# Frontend Art Direction Ops

## Trigger

Use when:
- a product UI feels visually weak, generic, or inconsistent
- the user asks to make a frontend look premium or "high-end"
- implementation keeps drifting because design choices were never locked

Do not use when:
- the task is purely backend architecture
- the user already provides final locked design files with exact specs

## Inputs

- Required: product context, target page/surface, conversion goal
- Optional: competitor references, brand constraints, existing design system

## Workflow

1. Lock the visual thesis in one sentence (mood + structure + interaction energy).
2. Build a compact reference board:
   - 6-10 inspiration screens for composition
   - 4-6 reference patterns for app interaction and forms
3. Define token-level decisions:
   - primary/secondary typefaces
   - 4-6 color tokens
   - spacing/radius/shadow scales
4. Define section responsibilities:
   - hero/workspace
   - support/proof
   - conversion/final action
5. Define motion budget (2-3 meaningful transitions) and ban ornamental effects.
6. Hand off an implementation-ready style spec before coding starts.

## Output Contract

- visual thesis
- reference board shortlist
- token decisions (type/color/spacing/radius/shadow)
- section-level layout plan
- interaction and motion plan
- explicit "do not add" list to prevent design drift

## Guardrails

- Prefer a clear composition over extra components.
- Use restrained color and motion systems.
- Keep readability and interaction clarity above decoration.
- Treat mobile and desktop as first-class surfaces, not afterthoughts.
