---
name: website-page-planning-ops
description: Turn a rough website or marketing-site idea into a concrete page plan with section roles, CTA structure, and a compact design brief.
memory_tags:
  - domain:frontend-design
  - workflow:page-planning
  - skill_role:generator
  - repo_boundary:tools
  - inputs:site-brief
  - outputs:page-plan
  - risk:medium
---

# Website Page Planning Ops

## Trigger

Use when:
- the user wants to design a website but the page structure is still fuzzy
- the assistant needs to decide whether the project should be a one-page site, a marketing site, or a multi-page brand site
- a design tool like Pencil needs a tighter brief before generation

Do not use when:
- the user already has a locked sitemap or final wireframes
- the task is purely visual styling rather than page/content planning

## Inputs

- Required: product or site concept, target audience, primary conversion goal
- Optional: brand tone, existing content, asset constraints, launch scope

## Workflow

1. Restate the site in operational terms:
   - what the site is for
   - who it is for
   - what action it must drive
2. Ask a small set of follow-up questions only where the answers change structure:
   - one page vs multi-page
   - trust/proof requirements
   - pricing, FAQ, contact, blog, or app-login needs
   - real content vs placeholder content
3. Recommend the page set and priority order.
4. For each page, define:
   - page job
   - primary CTA
   - required sections
   - reusable blocks shared across pages
5. Define content and imagery rules:
   - stock, AI, existing assets, or text-only
   - where placeholders are acceptable
6. Produce a compact handoff brief for downstream design or generation tools.

## Output Contract

- recommended page list with priority
- page-by-page purpose and CTA
- section outline for each page
- shared content/component rules
- imagery/content constraints
- compact Pencil-ready or frontend-ready brief

## Guardrails

- Keep the page set minimal for the current launch scope.
- Ask fewer questions when the site can be inferred safely.
- Prefer page responsibilities over copywriting flourishes.
- Separate page planning from visual direction; hand off to art-direction work when needed.
