---
name: clothing-cutout-ops
description: Create consistent transparent garment sprites for wardrobe catalogs from real photos, outfit-video frames, or verified product references. Use when adding clothing images or matching an existing wardrobe collection.
metadata:
  memory_tags:
    - domain:design
    - workflow:clothing-cutouts
    - skill_role:generator
    - repo_boundary:tools
    - inputs:garment-reference
    - outputs:transparent-png
    - risk:medium
---

# Clothing cutouts

Build one isolated garment asset per catalog piece. Match the collection's hanger treatment, framing, lighting and scale while preserving observed garment construction.

## Establish the garment and style

Inspect the source image before generation. Separate the garment reference from the collection style reference. Identify visible color, cut, closure, pocket layout, sleeve or inseam length, and distinctive details. User corrections outrank a generated image. Do not turn a button or snap-front jacket into a zipper jacket, or a short-sleeve T-shirt into a sweatshirt.

Use a real flat-lay or product photo when the user supplies an exact one. Otherwise use the available image-generation tool to create a source-guided reconstruction. Follow the imagegen skill for tool invocation, transparent output and saving. Do not substitute an outfit screenshot for a requested garment cutout.

When product identity matters, use purchase evidence or an official product page if available and authorized. A receipt proves a purchase, but does not by itself prove which of several similar items appears in a video. Ask a targeted identity question when necessary; continue unrelated garments while waiting. Keep uncertain models tentative. Keep receipts, account data and order links private; publish only deliberate catalog details.

## Match the collection

Resolve hanger treatment from the existing accepted collection or user direction: all assets with embedded hangers, all garment-only assets with a shared UI hanger, or another explicit consistent convention. Do not mix embedded wood hangers with a different wire overlay. For trousers and shorts, a matching wooden clip hanger may differ in shape while retaining wood and hook style. Resolve shoes separately rather than inventing a clothing construction.

Prefer a separate generation/edit call per garment. For existing sprites, preserve the garment and change only the requested hanger or detail. Ask for genuine alpha transparency, no wearer, room, caption, watermark or unrelated garments. Specify the complete garment and hook within the frame, with comparable small margins. Avoid invented logos and unseen construction.

Useful prompt skeleton:

> Garment reference: image 1. Style reference: image 2. Preserve [observed construction and color]. Produce one front-facing isolated [garment] with [chosen hanger treatment], entirely visible, centered with comparable framing. Genuine transparent background. No person, room, text, unrelated clothing or invented branding. [For edits: change only the requested element; preserve the rest.]

## Verify and integrate

Inspect each result against the garment evidence, not just the previous generated sprite. Check closure, silhouette, color, pockets, logos, full hook and hem, alpha edges, stray neighboring garments and unintended text. Reject a material mismatch; regenerate with a specific correction. Label uncertain reconstructions honestly.

Copy accepted files into the consuming project with stable versioned filenames. Retain original references privately and record the source, tool, prompt, confidence, corrections and asset hash in project provenance. Preserve existing files unless replacement was requested.

Inspect the whole rack as well as individual PNGs: identical attachment baseline, consistent hanger family, selected-only lift, no duplicate hooks, comparable visual scale, and no image cropping. Check detail and catalog views too. A successful image generation is not completion until the catalog references the accepted asset and the site build includes it.
