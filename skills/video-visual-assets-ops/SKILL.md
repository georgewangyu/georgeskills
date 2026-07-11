---
name: video-visual-assets-ops
description: Design and produce richer visual assets for selected short-form or long-form video beats, including coded motion graphics, diagrams, screen demonstrations, official promo excerpts, generated stills, and generated video. Use when an explicit visual work order needs more explanatory power, novelty, humor, or motion than a screenshot can provide, or when a video asset pack identifies a small number of high-value custom visual opportunities; use the asset-pack skill instead for whole unsorted scripts.
memory_tags:
  - domain:social-media
  - workflow:video-visual-assets
  - skill_role:generator
  - repo_boundary:tools
  - inputs:visual-work-order
  - outputs:editor-assets
  - risk:medium
---

# Video Visual Assets Ops

Turn selected script beats into concise visual treatments and rendered editor assets. Prefer deterministic, editable, source-safe production paths before expensive generation.

## Input Gate

Resolve:

- one exact script beat or a small set of selected visual work orders and their intended meaning
- target duration, aspect ratio, and safe margins
- output directory and naming reservation
- whether the visual is evidence, explanation, atmosphere, or comedy
- source material, brand constraints, and available generation tools

If several beats are candidates, rank them by comprehension gain, hook value, production burden, and source risk. Build only the highest-value assets first.

## Choose the Production Path

Use [production-paths.md](references/production-paths.md) to select one of:

1. source-faithful screen recording or UI demonstration
2. official promo or demo excerpt
3. deterministic coded motion
4. diagram or comparison board
5. generated still or stylized plate
6. generated video

Use screenshots or A-roll when motion adds little. A visual is successful when it clarifies the beat in one glance or creates a deliberate pattern interrupt.

## Workflow

### 1. Write a micro-storyboard

For each selected beat, define:

- first frame
- one visual change or reveal
- final frame
- duration
- narration sync point
- text hierarchy
- provenance or synthetic-media label

Keep most inserted motion between 1.5 and 5 seconds. Avoid miniature explainer films inside a short unless the visual is the premise.

### 2. Fan out when paths are independent

Use available subagents for bounded lanes such as:

- visual-concept alternatives
- official source/promo inventory
- coded animation implementation
- independent legibility and motion QA

Give each worker a reserved filename or staging directory. Do not have multiple workers edit the same source file. The parent selects the concept, merges provenance, and performs final visual inspection.

### 3. Prefer reversible local prototypes

Without additional approval, create lightweight local drafts using available code, SVG/HTML/CSS/canvas, `ffmpeg`, screen capture, or existing generation entitlements when the user already asked for asset production.

Ask before:

- billable image or video generation
- long generated-video jobs
- large source-media downloads
- generation that materially changes the factual framing

Do not pause for approval merely to make a small local poster frame, motion test, or storyboard.

### 4. Preserve truth and provenance

- Never generate a fake receipt, article, benchmark, product UI, or social post.
- Do not present generated footage as a real event, person, product demonstration, or historical record.
- Keep synthetic visuals clearly separated from evidence assets in the manifest.
- Prefer official press kits, product pages, or creator-owned source footage for promo excerpts.
- Record source URL, owner, downloaded file, excerpt in/out points, and any visible watermark or usage limitation.
- Use the shortest excerpt that performs the editorial job.

### 5. Compose existing skills

- Use `social-motion-diagram-ops` for sketch-style diagrams and small looping flows.
- Use `social-video-archive-ops` when official or reference video must be downloaded and preserved; create only the short editor-ready derivative here and retain exact in/out points.
- Use an image-generation skill for generated stills or image edits when available.
- Use the active browser or screen-control skill for real UI demonstrations.
- Return to `video-asset-pack-ops` so the rendered files and provenance enter the numbered manifest.

### 6. Render editor-ready deliverables

Prefer:

- PNG poster or first frame
- MP4 for motion and generated video
- editable SVG, HTML/CSS, or source project when practical
- alpha-capable formats only when the editor workflow supports them

Use stable names such as:

- `NN_<beat>_poster.png`
- `NN_<beat>_motion.mp4`
- `NN_<beat>_source.svg`
- `NN_<beat>_promo_excerpt.mp4`

### 7. Verify

Inspect the first, middle, and final frames. Verify dimensions, duration, frame rate, file size, readable text, safe margins, clean loops, and absence of blank frames. Confirm that the visual still makes sense with the sound off.

## Output Contract

Return:

- ranked visual concepts and chosen production path
- rendered asset paths
- editable source paths when available
- duration, dimensions, and verification results
- provenance or synthetic-media status
- exact timeline placement and narration sync point
- approval-required concepts that were not run

## Guardrails

- Do not build motion solely to make the edit busier.
- Do not let custom visuals block the usable first edit.
- Do not imitate a living creator's proprietary style exactly; extract general visual mechanics.
- Do not conceal missing evidence with generated media.
- Do not invoke paid or scarce generation silently.
- Do not copy private media into public repositories.
- Do not own project folders, raw-media intake, narration lock, or whole-video coverage decisions.
