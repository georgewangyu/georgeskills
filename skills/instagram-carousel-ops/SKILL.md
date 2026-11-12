---
name: instagram-carousel-ops
description: Create branded Instagram carousel assets from a topic, blog, source post, or script, including static PNGs, short MP4 motion pages, editable design references, contact sheets, and posting-ready notes.
memory_tags:
  - domain:social-media
  - workflow:instagram-carousel
  - skill_role:generator
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
   - Recover any earlier carousel, editable source, and source-reference notes before inventing a new look. Record the exact files and distinguish an observed reference from an inferred pattern. Verify product claims against primary material or a documented hands-on test.

2. Build a slide brief before designing.
   - Default to `5-7` slides for a first draft unless the user requests another length.
   - Use a hard-claim cover, then problem, framework, proof/contrast, and CTA.
   - Keep one idea per slide and make each slide readable as a standalone screenshot.
   - Name the format route. For a **Chris Pathway carousel type**, use a real creator portrait or frame on a specific, countable cover. Make every numbered interior page image-led: a real photo or frame of the work setting plus a relevant, inspectable resource, object, or example. Put a short title near the top and one useful line near the bottom. The image must help explain that particular tip; a generic laptop photo behind a large text card does not qualify. Close with the actual next step. Borrow the progression, not another creator's likeness, exact layout, or copy. For a **proof-led walkthrough**, use problem, action, screenshot/receipt, result, and limitation instead. Choose the route that fits the evidence.
   - For any promised comment-keyword resource, inventory the exact deliverable and fulfillment path before writing the CTA. If it does not exist, use a save, reply, or question CTA that can be honored now.

3. Choose the design route.
   - Use repo-owned HTML/CSS/SVG plus an allowed deterministic renderer when precise exports, animation, or repeatable variants matter. Follow the workspace's browser and renderer rules.
   - Use Pen/Pencil for editable static references, design-language boards, option boards, and future-facing visual systems, especially when a human will revise the composition.
   - For the Chris Pathway route, first inspect the creator's own previous carousel and inventory owned photos, video frames, and genuine source screens for each page. Preserve the creator's portrait presence and clear, countable hierarchy. Make the photo or frame fill the slide edge to edge by default; place the short title and caption directly over it with local gradients or shadows for legibility. Avoid white page borders, header/footer bands, and boxed photo cards unless the creator requests them. A product accent color may shape type and small rules, but should not replace the full-bleed photographic composition. For a product-specific post, inspect the product's current primary visual source and choose a restrained palette that fits it; do not carry over an unrelated accent color or fake its interface. If owned imagery is insufficient, choose licensed photography with recorded source and usage rights, and reject polished stock that makes a personal post feel like an ad. An editorial reference can guide spacing and hierarchy, but the creator's actual scenes should carry the page. Imagegen can replace private readable content on a real work screen with generic, non-readable illustration when the creator authorizes it; preserve the original separately, document the edit, and never present the generated screen as product proof. Use a legitimately available photo or video frame when the post depends on a real person's identity. Preserve likeness and provenance; never use imagegen to imply a documentary product screen, completed result, or event. Keep text, screenshots, logos, and proof in an editable or deterministic layout layer.
   - Use Canva only as an optional polish/handoff layer when a Brand Kit, template, or collaboration workflow already exists. Do not make Canva the only source of truth unless the user explicitly asks for that.

4. Create a new variant folder.
   - Preserve old drafts and old design-language options.
   - Name variants clearly, such as `draft/v1-static`, `draft/motion-test`, or `draft/redesign-v2`.
   - Put source files, exported assets, and notes in the variant folder.

5. Add a creator or human anchor when appropriate.
   - For personal-brand content, prefer a portrait, short talking-head loop, or screen/video snippet on the cover or CTA.
   - If no usable media exists, create a placeholder and document the missing asset instead of silently making the post feel generic.
   - Keep framework and proof slides scannable. On an image-led route, preserve enough visible photography that the result reads as a scene, not a quote card. Use distinct crops, objects, or genuine screens where they clarify different items; do not repeat an unrelated background as filler.

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
   - Check every claim against its recorded source, and label a proposed use case as a proposal until demonstrated. Verify that a real portrait is the intended person and that product screens are genuine, current, and safe to show.

9. Prepare posting notes.
   - List the selected media files in order.
   - Include the account/brand to post from when known.
   - Include public hosting or upload requirements for any API/posting bot.
   - If the user approves actual publishing, load any project-local private
     media-hosting or account overlay before creating public URLs. Prefer a
     local `IGBOT_MEDIA_HOSTING_WORKFLOW.md` when present.
   - Do not publish until the user explicitly approves the final assets and caption.

10. Document what changed.
    - Update the local design-language docs with the design option, constraints, and source links.
    - Add a short retro for new first-of-kind workflows: what worked, what failed, what to reuse, and what to improve.
    - If a new durable pattern emerges, update this skill or its references.

## First concept gate

For a new format or topic, first show the cover options, ordered slide copy, one representative visual or contact sheet, evidence gaps, and a recommended production route. Get creator feedback on that concept before building a full polished render. Keep private examples and source-media provenance with the owning project, not in this reusable skill.

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
- On an image-led series, inspect each interior page at phone size: the photo or resource should carry information, the headline should remain readable, and any illustrative screen must be labeled so it cannot be mistaken for a verified product result.

## Guardrails

- Do not overwrite older variants unless the user explicitly asks.
- Do not publish or queue a post without explicit approval.
- Do not hardcode private handles, emails, account IDs, tokens, private URLs, or absolute local paths into this reusable skill.
- Do not use a static-only result when the user asked for GIF-style or video carousel pages.
- Do not rely on third-party logos as decoration.

## References

- `references/design-language-patterns.md`: reusable visual and storytelling patterns.
- `references/platform-publishing.md`: Instagram carousel and MP4 publishing constraints to verify before posting.
