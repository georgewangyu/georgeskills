---
name: social-motion-diagram-ops
description: Create Excalidraw-style static diagrams and short looping motion diagram assets for LinkedIn, X/Twitter, newsletter, or social draft posts.
memory_tags:
  - domain:social-media
  - workflow:motion-diagram
  - inputs:draft
  - outputs:visual-asset
  - repo_boundary:tools
  - risk:medium
---

# Social Motion Diagram Ops

## Trigger

Use when:
- A user wants an Avi/DailyDose-style sketch diagram, animated diagram, GIF-like image, or motion graphic for a LinkedIn/X/social draft.
- A user asks to turn an abstract technical/business idea into a visual explanation asset.
- A user wants a reusable visual system for posts, threads, carousels, or newsletter visuals.

Do not use when:
- The request is only for text copy with no visual asset.
- The user wants photorealistic imagery or illustration; use an image-generation or design skill instead.
- The user asks to copy a creator's exact proprietary source file or brand identity. Borrow the pattern, not the private asset.

## Inputs

- Required: draft text, thesis, or concept to visualize.
- Optional: platform (`x`, `linkedin`, `newsletter`), output format (`static`, `mp4-loop`, `gif`, `carousel`), aspect ratio, brand palette, existing logo/source diagram, and output folder.

## Workflow

1. Extract one visual claim from the draft.
   - Prefer a process, loop, contrast, stack, lifecycle, or before/after.
   - If there are multiple claims, choose the one that makes the post easiest to understand in one glance.
2. Pick the visual form.
   - `loop`: circular or rectangular flow with one moving marker.
   - `pipeline`: left-to-right staged boxes with state transitions.
   - `contrast`: manual vs automated, old vs new, fragile vs robust.
   - `stack`: layers, guardrails, or components surrounding a core.
3. Build a mostly static sketch-style diagram.
   - Use white/off-white background, hand-drawn-looking boxes, simple icons, muted accent colors, and dense but readable labels.
   - Keep the main idea legible when viewed as a still image.
   - Avoid marketing hero layouts, decorative gradients, and generic stock visuals.
4. Add minimal motion only where it explains flow.
   - Animate a dot, highlight, checkmark, pulse, or small icon state.
   - Keep the loop short: usually 1.5-4 seconds, 12-24 fps.
   - Make the first and last frames visually compatible so it loops cleanly.
5. Choose the production path.
   - Default deterministic path: SVG/HTML/CSS/canvas source -> browser-rendered frames -> `ffmpeg` MP4 loop -> PNG poster.
   - Editable design handoff: use Pencil MCP for structured static layouts when a `.pen` design is active or requested.
   - Canva handoff: use Canva for editable social wrappers, brand-kit polish, resizing, or converting a flat poster into an editable design.
   - Do not depend on Canva/Pencil for precise frame-by-frame motion unless their exposed tool surface supports it in the current session.
6. Produce practical social assets.
   - Preferred source: editable SVG/HTML/CSS or `.excalidraw` when feasible.
   - Preferred final: MP4 for X/LinkedIn, plus PNG poster frame.
   - Optional: GIF only when explicitly requested; MP4 is smaller and usually displays better.
7. Verify before handoff.
   - Inspect dimensions, duration, frame rate, and file size with `ffprobe` or an equivalent tool.
   - Open or sample frames locally to ensure text is readable, no labels overlap, and motion is visible.
   - If used on social, keep safe margins for platform cropping.

## Output Contract

Return:
- The asset paths created or updated.
- The concept/storyboard in 3-6 bullets.
- A concise note on what is editable and what is rendered.
- Any verification performed, including dimensions/duration for motion assets.

Default asset naming:
- `<slug>-diagram.svg`
- `<slug>-poster.png`
- `<slug>-loop.mp4`
- `<slug>-loop.gif` only when requested

## Capability Notes

- The agent can create these assets directly with SVG/HTML/CSS/canvas and render them via local browser tooling or `ffmpeg` when available.
- Pencil MCP can help create or export structured static design layouts, but the currently exposed surface is strongest for layout and image export, not precise animation authoring.
- Canva can help make editable social graphics and platform variants, but deterministic motion timing is usually better handled with code-rendered SVG/HTML plus `ffmpeg`.
- The agent can draft Excalidraw-style JSON/SVG, but exact parity with a creator's private Excalidraw file is not guaranteed without the source.
- The strongest version usually combines human taste in the static diagram with deterministic rendering for the motion export.

## References

- Read `references/style_recipe.md` when designing the visual system or explaining why the pattern works.
- Read `references/export_specs.md` when rendering or validating platform-ready outputs.
- Read `references/inspiration_and_limits.md` when the user references the Avi/DailyDose loop diagram pattern or asks what can/cannot be replicated.

## Boundaries

- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, private URLs, or user-specific output paths.
- Use generic placeholders such as `<brand>`, `<draft-slug>`, and `<output-dir>`.
- Private draft storage and account-specific posting workflows belong in the invoking private repo, not this skill.
