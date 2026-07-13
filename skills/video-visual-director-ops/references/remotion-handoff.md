# Remotion Handoff

Remotion is the precision-animation and assembly layer for treatments that need
exact timing, repeatability, or a live browser preview. It is not the default
generator for cinematic or metaphorical footage when an approved consumer
Gemini video surface is the better visual fit.

## Runtime And Project Layout

Use the configured shared Remotion runtime and dependency installation. Do not
create `node_modules`, install Remotion, or duplicate the runtime inside a
video project. Keep only project-specific source and data beside the video
workspace:

```text
visual-pass/
  remotion/
  inputs/a_cut_vNN.mp4
  plan/visual-edit-plan.json
  outputs/
  qa/
```

Run the shared runtime against the project-specific composition. Route
disposable builds to the configured shared temporary-build directory, not the
video folder.

Use one shared composition-level timebase. Convert seconds to frames once and preserve the chosen frame rate. Give sequences stable beat IDs matching the edit plan.

## Delivery Choices

- Full composite: include the A-cut with Remotion's video component, then apply crops, scale, position, overlays, captions, audio, and motion.
- Alpha overlay: render only transparent layers. For ProRes 4444, use PNG image frames and an alpha-capable pixel format/profile as required by the installed Remotion skill.
- Individual assets: render named sequences with handles when manual placement benefits from them.
- CapCut finishing bundle: render a review composite plus reusable alpha or
  individual layers, then describe unbaked A-roll moves and every placement in
  `CAPCUT_HANDOFF.md` so editability is explicit.

An asset bundle is not a native CapCut edit. When native CapCut tracks are the
declared target, use Remotion only to create the selected motion assets. Import
those assets, text layers, and overlays into the versioned CapCut draft; verify
the reopened timeline; and export the review candidate from that draft.

## Live Review Loop

1. Start Remotion Studio from the project.
2. Share the local preview in the available browser surface.
3. Change data, props, or sequence components while the creator reviews.
4. Inspect representative stills and benchmark a `5-10s` sample before full renders.
5. Project the full-render time from the sample and switch to individual assets
   or segmented hardware-accelerated assembly when a full Remotion composite
   is unnecessarily expensive.
6. Keep the last accepted render and never overwrite it silently.

## Timing Invalidation

If a new A-cut arrives, compare its fingerprint and duration. Do not assume old timecodes survive. Re-align the transcript, regenerate or rebase the beat map, then rerender. Visual-only changes can iterate without reopening the A-cut.
