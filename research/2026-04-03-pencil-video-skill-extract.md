---
title: "Pencil.dev video skill extract"
date: 2026-04-03
source_video: "https://www.youtube.com/watch?v=DFcvz2kcR74"
source_transcript_label: "How-I-Turned-Claude-Into-a-Design-Tool-with-Pencil.dev-DFcvz2kcR74.txt"
---

# Pencil.dev Video Skill Extract

## What the video actually shows

The video demonstrates two usable patterns:

1. A guided website planning flow before design generation.
2. A Pencil MCP execution flow for generating, editing, and handing designs off to code.

It does not show the full body of the creator's "superpowers" skill. The only visible signal is that the skill asks follow-up questions before generating pages.

## Extracted Workflow 1: Website Page Planning

Observed flow:

1. Start from a blank frame.
2. Set or adjust the target frame size.
3. Ask the assistant to use a style guide.
4. Prompt for a site concept, for example a "bohemian-style French bakery".
5. Let a planning skill ask follow-up questions about the website.
6. Have the assistant decide or confirm the page set.
7. Generate multiple pages, not just one landing page.
8. Review and manually tweak text/layout in Pencil.
9. Hand the design off to code generation.

Hidden but inferable planning questions:

- What kind of site is this: landing page, marketing site, app shell, multi-page brand site?
- Which pages are needed first?
- What is the primary CTA?
- What tone and visual direction should the site follow?
- Should imagery come from stock, AI, or existing assets?
- What content is real versus placeholder?

## Candidate Skill: `website-page-planning-ops`

Purpose:
Turn a loose site idea into a concrete page plan before Pencil starts drawing.

Trigger:

- The user wants to design a website in Pencil from a rough idea.
- The assistant needs to decide whether the site should be one page or multiple pages.
- The prompt is too vague to generate good page structure directly.

Inputs:

- Site/product concept
- Audience
- Conversion goal
- Optional brand/style cues
- Optional content/assets constraints

Workflow:

1. Clarify the site type and business goal.
2. Ask 5-8 follow-up questions only where the answers materially change page structure.
3. Produce a recommended page list with priorities.
4. Define each page's job, key sections, and CTA.
5. Define shared content/asset rules:
   - stock vs AI imagery
   - real copy vs placeholder
   - reuse of testimonials, pricing, FAQ, contact blocks
6. Hand off a compact design brief for Pencil generation.

Output contract:

- recommended page set
- page-by-page purpose
- section outline per page
- primary CTA map
- content and imagery rules
- compact Pencil-ready prompt

Why it is worth adding:

- It fills a gap between vague brainstorming and visual generation.
- It complements `frontend-art-direction-ops` instead of replacing it.
- It is useful outside Pencil too.

## Extracted Workflow 2: Pencil MCP Design Flow

Observed flow:

1. Open Pencil and choose either:
   - an existing UI kit and components, or
   - a blank file for a from-scratch design
2. If using a UI kit, point the model at the available components.
3. If designing from scratch, apply a style guide first.
4. Copy the Pencil prompt into the terminal assistant that already has preferred skills and MCP servers.
5. Explicitly tell the assistant to use the Pencil MCP server.
6. Let the assistant generate via Pencil tools, especially `batch_design`.
7. Watch the design render live in Pencil.
8. Manually tweak spacing, copy, or layout in the editor.
9. Ask the assistant to translate the Pencil design into code.
10. Connect the coded result to real data or other MCP-backed systems if needed.

Important operational detail:

- The creator prefers using Pencil through the terminal assistant so Pencil can benefit from the same skills, MCP servers, and workflow habits already in use.

## Candidate Skill: `pencil-design-orchestration-ops`

Purpose:
Provide a reliable operating procedure for using Pencil MCP from the coding agent.

Trigger:

- The user wants a page, dashboard, or app surface designed in Pencil.
- The user wants to use Pencil from the terminal agent instead of Pencil's own chat.
- A design should be editable in Pencil before code is finalized.

Inputs:

- Design target
- Whether to use an existing UI kit or blank canvas
- Optional style guide
- Optional page plan or product brief

Workflow:

1. Decide the mode:
   - UI kit composition
   - blank-canvas art direction
   - import-from-Figma refinement
2. Prepare the canvas:
   - select frame
   - set width/height
   - inspect available components or styles
3. Build a concise generation prompt grounded in:
   - page goal
   - target sections
   - component constraints
   - image/content source rules
4. Run Pencil MCP generation, preferring structured tool usage over vague prose.
5. Review the result in-editor and identify manual polish changes.
6. Freeze the design intent before code handoff.
7. Translate the design into frontend code with one-to-one fidelity where appropriate.

Output contract:

- selected Pencil mode
- generation prompt
- design constraints used
- review notes / polish queue
- code handoff brief

Why it is worth adding:

- It turns "use Pencil MCP" into a repeatable workflow.
- It provides the missing bridge between design generation and frontend implementation.
- It would pair cleanly with the existing SaaS/frontend skills.

## Fit Against Existing Skills

Closest existing skills in `georgeskills`:

- `frontend-art-direction-ops`
- `saas-template-fit-ops`

Likely split of responsibilities:

- `website-page-planning-ops`: decide what pages/sections should exist.
- `frontend-art-direction-ops`: decide how the experience should feel visually.
- `pencil-design-orchestration-ops`: execute the design workflow in Pencil.
- existing frontend/coding flow: translate approved design into the real app.

## Recommendation

If you want to add only one new skill first, add `pencil-design-orchestration-ops`.

If you want the stronger pair, add both:

1. `website-page-planning-ops`
2. `pencil-design-orchestration-ops`

That gives you a cleaner sequence:

1. Plan the site/pages.
2. Lock the visual direction.
3. Generate and refine in Pencil.
4. Translate into production frontend code.
