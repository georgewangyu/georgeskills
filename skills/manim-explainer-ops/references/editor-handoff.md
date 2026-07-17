# Editor Handoff

Complete `MANIM_HANDOFF.json` beside the rendered asset. Keep the Python source,
configuration, and dependency file with the output so another editor or agent
can reproduce the render.

## Required Fields

- project and scene class
- `explanation`, `evidence`, or `synthetic illustration` classification
- exact teaching claim
- source URLs or data provenance for factual values
- timeline in/out and the spoken sync phrase
- render command and output path
- poster path
- duration, dimensions, frame rate, and codec
- first/middle/final frame, safe-zone, narration-sync, and conceptual checks
- manual editor steps and known limitations

## Output Rules

- Prefer H.264 MP4 for ordinary full-frame editor assets.
- Produce alpha only after testing the receiving editor, codec, pixel format,
  and actual composite. Preserve a non-alpha review render as proof.
- Use a frame-extracted PNG as the poster when the animation has a useful key
  state. Record its timestamp.
- Keep full-frame backgrounds out of overlay renders.
- Do not bake private footage into a public scaffold or reusable example.

## Integration

Register the render and poster in the parent video's numbered asset manifest.
Return the exact placement and narration cue to `video-visual-director-ops` or
the active editor handoff. The whole edit remains owned by that workflow.
