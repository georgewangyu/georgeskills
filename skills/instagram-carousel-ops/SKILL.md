---
name: instagram-carousel-ops
description: Create branded Instagram carousel assets from a topic, blog, source post, or script, including static PNGs, short MP4 motion pages, editable design references, contact sheets, and posting-ready notes.
memory_tags:
  - domain:social-media
  - workflow:instagram-carousel
  - outputs:visual-assets
  - repo_boundary:tools
  - risk:medium
---

# Instagram Carousel Ops

## Overview

Use this skill when the user asks for an Instagram carousel, 4:5 social carousel, branded slide pack, mixed image/video carousel, carousel design language, or a repeatable carousel workflow from a blog, transcript, topic, or source post.

The goal is a reusable carousel system, not just a one-off set of slides: preserve design variants, document decisions, render inspectable assets, and leave enough structure that the next carousel can reuse the same standards.

## Workflow

1. Confirm the source and objective.
   - Identify the topic, source blog/post/transcript, target account, audience, and desired CTA.
   - If the user provided an example carousel or Reel, treat it as workflow/style inspiration unless they explicitly ask to copy its visual style.
   - Resolve brand defaults from the local/private project when available. Do not hardcode personal handles, account IDs, or private paths into the reusable skill.

2. Build a slide brief before designing.
   - Default to `5-7` slides for a first draft unless the user requests another length.
   - Use a hard-claim cover, then problem, framework, proof/contrast, and CTA.
   - Keep one idea per slide and make each slide readable as a standalone screenshot.

3. Choose the design route.
   - Use repo-owned HTML/CSS/SVG plus Playwright or another deterministic renderer when precise exports, animation, or repeatable variants matter.
   - Use Pencil for editable static references, design-language boards, option boards, and future-facing visual systems.
   - Use Canva only as an optional polish/handoff layer when a Brand Kit, template, or collaboration workflow already exists. Do not make Canva the only source of truth unless the user explicitly asks for that.

4. Create a new variant folder.
   - Preserve old drafts and old design-language options.
   - Name variants clearly, such as `draft/v1-static`, `draft/motion-test`, or `draft/redesign-v2`.
   - Put source files, exported assets, and notes in the variant folder.

5. Add a creator or human anchor when appropriate.
   - For personal-brand content, prefer a portrait, short talking-head loop, or screen/video snippet on the cover or CTA.
   - If no usable media exists, create a placeholder and document the missing asset instead of silently making the post feel generic.
   - Keep framework and proof slides diagrammatic enough that the carousel remains scannable.

6. Produce static and motion outputs.
   - Default frame: `1080 x 1350`.
   - Export PNG posters for review and fallback.
   - For GIF-style motion, export MP4 carousel pages, not `.gif`, unless the user only needs a preview.
   - Keep motion loops short, usually `2-4s`, and make the first frame work as a still image.

7. Brand the system.
   - Include the account handle, a slide count, and a compact brand mark or recurring visual signature.
   - Use vendor logos only when the post is intentionally about those vendors and usage is appropriate.
   - For generic AI/tool references, prefer text chips such as `CODEX`, `CLAUDE`, or `GPT` over official marks.

8. Verify the exports.
   - Generate a contact sheet.
   - Check dimensions, duration, and frame rate for every media file.
   - Inspect representative frames or screenshots for overlap, clipped text, weak contrast, and broken motion.
   - Re-render after any copy, handle, brand, or asset correction.

9. Prepare posting notes.
   - List the selected media files in order.
   - Include the account/brand to post from when known.
   - Include public hosting or upload requirements for any API/posting bot.
   - Do not publish until the user explicitly approves the final assets and caption.

10. Document what changed.
    - Update the local design-language docs with the design option, constraints, and source links.
    - Add a short retro for new first-of-kind workflows: what worked, what failed, what to reuse, and what to improve.
    - If a new durable pattern emerges, update this skill or its references.

## Output Contract

For a production-ready carousel draft, leave:

- `README.md` or runbook for the variant.
- Source renderer/design file.
- Ordered PNG posters.
- Ordered MP4 pages when motion was requested.
- Contact sheet.
- Verification notes with dimensions and duration.
- Caption or posting draft when requested.
- A short note explaining whether Canva, Pencil, code rendering, or another tool was used.

## Quality Bar

- The cover should stop the feed with a specific claim, not a generic title.
- The palette should have enough contrast and personality to feel owned, but avoid a one-note color system.
- Text should be mobile-first and avoid paragraph blocks.
- Motion should clarify the idea: cursor movement, scan line, reveal, process marker, receipt stack, human loop, or short demo window.
- The carousel should feel like a branded recurring series, not a collection of unrelated quote cards.

## Guardrails

- Do not overwrite older variants unless the user explicitly asks.
- Do not publish or queue a post without explicit approval.
- Do not hardcode private handles, emails, account IDs, tokens, private URLs, or absolute local paths into this reusable skill.
- Do not use a static-only result when the user asked for GIF-style or video carousel pages.
- Do not rely on third-party logos as decoration.

## References

- `references/design-language-patterns.md`: reusable visual and storytelling patterns.
- `references/platform-publishing.md`: Instagram carousel and MP4 publishing constraints to verify before posting.
