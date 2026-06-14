# Inspiration And Limits

## Reference Pattern

Original reference:

- Avi Chawla X post: `https://x.com/_avichawla/status/2065727218991735000`
- Topic: loop engineering and agent harnesses.
- Observed media type: X labels it as an `animated_gif`, but the served asset is a short MP4.
- Observed dimensions: `1210x1138`.
- Observed duration: about `2.05s`.
- Observed frame rate: `20 fps`.
- Observed motion: mostly static Excalidraw-style diagram with a moving green flow marker and small state changes/checks.

Use this as an inspiration target for the operating pattern, not as a template to clone exactly.

## What To Replicate

- Dense sketch-style systems diagram.
- One clear animated path through the system.
- Short loop that makes the diagram feel alive without requiring narration.
- Strong poster frame that works even if autoplay fails.
- MP4 output that social platforms can display like a GIF.

## What Not To Replicate

- Do not copy the creator's exact diagram, labels, logo, or source styling.
- Do not claim access to the original Excalidraw/Figma/After Effects source.
- Do not depend on a proprietary workflow unless the user provides the source file or active design tool.

## Recommended Toolchain

Default:

1. Create a visual plan from the draft.
2. Generate SVG/HTML/CSS/canvas source.
3. Render frames in a local browser or canvas runtime.
4. Export MP4 with `ffmpeg`.
5. Export a PNG poster frame.
6. Optionally import the static poster or source into Canva/Pencil for editable social wrapping.

MCP-assisted variants:

- Pencil MCP: useful for static layout generation and high-quality PNG/JPEG/WEBP/PDF export from `.pen` files.
- Canva MCP/App: useful for editable social designs, brand-kit passes, resizing, and Magic Layers conversion from a flat image.
- Figma MCP, if available in a future session: likely useful for editable source design and component management, but still verify animation/export support before promising deterministic loops.

## Current Limitations

- Precise motion export is more reliable through code and `ffmpeg` than through the currently exposed Pencil/Canva MCP surfaces.
- Editable visual source and rendered motion source may be separate artifacts.
- Text-heavy diagrams need manual taste checks for mobile readability.
- Excalidraw-style output can be approximated with SVG/HTML; exact Excalidraw parity may require generating or editing a real `.excalidraw` file.

## Future Improvements

- Add a small reusable renderer script that takes a diagram JSON spec and emits SVG, PNG poster, MP4 loop, and contact sheet.
- Add platform presets for X square, LinkedIn 4:5, newsletter 16:9, and GitHub/social preview.
- Add a validation rubric for mobile text size, safe margins, and first-frame quality.
- Add optional import/export bridges for Pencil, Canva, or Figma when their tool surfaces support the needed source format.
