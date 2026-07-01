---
name: video-companion-page-ops
description: Create local HTML/blog-style companion pages for educational long-form videos, explainers, demos, and presentation-style recordings. Use when the user wants a first local page that explains a topic, includes clickable source/screenshot sections, supports a talking outline, and may later become a deployed website, blog post, or SEO artifact.
memory_tags:
  - domain:publishing
  - workflow:video-companion-page
  - skill_role:generator
  - repo_boundary:tools
  - inputs:video-context
  - outputs:companion-page
  - risk:medium
---

# Video Companion Page Ops

## Trigger

Use when:
- the user is preparing an informational or educational video and wants a local HTML artifact first
- the page should work as a blog post, presentation aid, demo script, or later deployable website page
- the page needs clickable source cards, screenshots, diagrams, or section navigation for filming
- the user is deciding between slides, a blog post, and an interactive explainer

Do not use when:
- the task is only thumbnail design, video editing, or short-form talking points
- the user already has a finished webpage and only wants frontend polish
- the user asks for a general marketing landing page rather than a companion explainer

## Inputs

- Required: video topic, target audience, working thesis, local project or destination
- Optional: sources, screenshots, transcript, talking points, existing design system, deployment target

## Workflow

1. Define the companion artifact's job:
   - teach the concept clearly enough to film from it
   - preserve sources and receipts
   - create a deployable or reusable page later
2. Pick the output shape:
   - blog-style explainer for durable public value
   - presentation-style sections for filming
   - hybrid page when the user wants both
3. Create or choose the local page location:
   - follow the active repo's web framework and route conventions
   - keep episode-specific assets beside the page or in the project's media folder
   - avoid deployment setup unless explicitly requested
4. Build the source spine:
   - collect primary sources before writing strong claims
   - capture or save source screenshots when visual proof helps the video
   - record source URLs and local asset paths
   - use self-made diagrams for the core explanation when third-party images would be tiny or unclear
5. Draft the page structure:
   - headline with the literal concept or claim
   - working definition
   - how it works
   - why it matters
   - concrete examples or receipts
   - edge cases, failure modes, or caveats
   - talking outline for the video
6. Add presentation affordances:
   - sticky or top section navigation
   - source cards that jump to screenshots or examples
   - large anchor sections that can be screen recorded
   - callouts for the creator's opinion separate from sourced facts
7. Implement with the local frontend stack:
   - reuse existing app layout, typography, and asset conventions
   - keep text readable at desktop recording size
   - avoid decorative clutter that makes screen recording harder
   - ensure every image has stable dimensions and cannot collapse the layout
8. Validate:
   - run the repo's relevant lint, build, or typecheck command when available
   - start or reuse a local dev server for framework apps
   - inspect the page in a browser at recording viewport size
   - fix broken images, overflowing text, and missing source links before handing off

## Page Pattern

Prefer this section model for first drafts:

1. `Hero`: title, one-sentence thesis, quick source/navigation chips.
2. `Definition`: compact explanation in plain language.
3. `Mechanism`: diagram or step-by-step flow.
4. `Receipts`: clickable source cards with screenshots.
5. `Opinion`: the creator's take, tradeoffs, and caveats.
6. `Talking Outline`: bullets that can become the video script.
7. `Next Decisions`: what still needs sourcing, design, deployment, or editing.

## Output Contract

Return:
- local page path and local URL if a dev server is running
- asset directory and source screenshot paths
- source links used
- validation commands run and their results
- remaining editorial or deployment decisions

## Guardrails

- Keep the page useful even before deployment.
- Do not bury the creator's take inside source summaries; label opinion clearly.
- Do not rely on tiny screenshots for core explanation; create diagrams or simplified blocks.
- Do not use unverified claims as headline hooks.
- Do not hardcode personal paths, handles, private repo names, credentials, or account-specific defaults inside reusable skill artifacts.
