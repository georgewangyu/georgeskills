# Remotion Handoff

Remotion is the default post-A-cut execution layer because it can render precise, repeatable treatments while the creator watches a browser preview.

## Project Layout

Keep the project beside the video workspace or under its `visual-pass/` folder:

```text
visual-pass/
  remotion/
  inputs/a_cut_vNN.mp4
  plan/visual-edit-plan.json
  outputs/
  qa/
```

Use one shared composition-level timebase. Convert seconds to frames once and preserve the chosen frame rate. Give sequences stable beat IDs matching the edit plan.

## Delivery Choices

- Full composite: include the A-cut with Remotion's video component, then apply crops, scale, position, overlays, captions, audio, and motion.
- Alpha overlay: render only transparent layers. For ProRes 4444, use PNG image frames and an alpha-capable pixel format/profile as required by the installed Remotion skill.
- Individual assets: render named sequences with handles when manual placement benefits from them.
- CapCut finishing bundle: render a review composite plus reusable alpha or
  individual layers, then describe unbaked A-roll moves and every placement in
  `CAPCUT_HANDOFF.md` so editability is explicit.

## Live Review Loop

1. Start Remotion Studio from the project.
2. Share the local preview in the available browser surface.
3. Change data, props, or sequence components while the creator reviews.
4. Inspect representative stills before full renders.
5. Keep the last accepted render and never overwrite it silently.

## Timing Invalidation

If a new A-cut arrives, compare its fingerprint and duration. Do not assume old timecodes survive. Re-align the transcript, regenerate or rebase the beat map, then rerender. Visual-only changes can iterate without reopening the A-cut.
