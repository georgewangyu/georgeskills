---
name: pencil-design-orchestration-ops
description: Run a repeatable Pencil MCP workflow to generate, refine, and hand off editable designs to frontend code.
memory_tags:
  - domain:frontend-design
  - workflow:pencil-orchestration
  - repo_boundary:tools
  - inputs:design-brief
  - outputs:pencil-design-handoff
  - risk:medium
---

# Pencil Design Orchestration Ops

## Trigger

Use when:
- the user wants to design a page, dashboard, or app surface in Pencil
- the user wants Pencil driven from the terminal agent rather than Pencil's built-in chat
- the design should remain editable in Pencil before coding is finalized

Do not use when:
- the task is pure frontend implementation with no design-generation step
- the user already has final locked design files and only wants code translation

## Inputs

- Required: target surface, product/context brief
- Optional: page plan, selected UI kit, style guide, image/content constraints

## Workflow

1. Choose the operating mode:
   - compose from an existing UI kit
   - design from a blank canvas
   - refine imported Figma content
2. Prepare the design context:
   - inspect active document or selected frame
   - set target frame size where needed
   - inspect available reusable components, styles, or variables
3. Build a compact generation brief that includes:
   - surface goal
   - required sections or modules
   - component/style constraints
   - image/content sourcing rules
4. Use Pencil MCP tools explicitly, preferring structured operations over vague prose:
   - inspect context first
   - generate with `batch_design`
   - read back results when validation is needed
5. Review the generated design in Pencil and note manual polish items:
   - spacing, hierarchy, copy fit, alignment, imagery
6. Freeze the approved design intent for implementation:
   - what should match 1:1
   - what can adapt to product reality
7. Hand the result off to frontend code with the design constraints preserved.

## Output Contract

- selected Pencil mode
- concise generation brief
- Pencil constraints and assumptions used
- review/polish notes
- implementation handoff notes for the frontend

## Guardrails

- Use Pencil as a design-stage accelerator, not a runtime dependency.
- Prefer existing UI-kit components when a kit is in scope.
- Keep the prompt grounded in page goals and constraints, not aesthetic adjectives alone.
- Validate the design before coding; do not assume the first generation is implementation-ready.
