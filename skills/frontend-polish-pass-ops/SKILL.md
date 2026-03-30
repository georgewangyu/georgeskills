---
name: frontend-polish-pass-ops
description: Run a final frontend polish pass for responsiveness, accessibility, hierarchy, copy clarity, interaction quality, and perceived performance before launch. Use when the UI is functional but not yet production-grade.
memory_tags:
  - domain:frontend-design
  - workflow:ui-polish
  - repo_boundary:tools
  - inputs:implemented-ui
  - outputs:polish-checklist
  - risk:medium
---

# Frontend Polish Pass Ops

## Trigger

Use when:
- the frontend works but still feels unfinished
- a launch page or app shell needs final visual and interaction quality checks
- the team wants a repeatable QA rubric for UI polish

Do not use when:
- there is no usable UI implemented yet
- the task is selecting product strategy rather than validating interface quality

## Inputs

- Required: running frontend or preview build
- Optional: design references, target devices, accessibility requirements

## Workflow

1. Run layout checks:
   - desktop and mobile viewport fit
   - spacing rhythm and alignment
   - text line length and hierarchy
2. Run interaction checks:
   - hover/focus/active/disabled states
   - keyboard navigation path
   - loading/empty/error states
3. Run readability and conversion checks:
   - headline clarity
   - CTA prominence
   - supporting copy precision
4. Run accessibility and performance checks:
   - contrast and focus visibility
   - semantic landmarks and labels
   - avoid unnecessary heavy assets or animation jank
5. Produce a prioritized polish list:
   - `must fix before launch`
   - `should fix soon`
   - `safe to defer`

## Output Contract

- prioritized issue list with severity
- concrete fixes with file-level pointers when possible
- final launch-readiness verdict
- explicit residual risk notes

## Guardrails

- Keep recommendations specific and implementable.
- Do not inflate low-impact issues.
- Prioritize fixes that improve clarity, trust, and conversion.
