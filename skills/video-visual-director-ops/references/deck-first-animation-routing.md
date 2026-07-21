# Deck-first animation routing

Use this reference after a portrait deck has established the approved visual
system for a multi-takeover video. Recheck current product behavior before a
production batch because export capabilities can change.

## Core rule

Do not use the animation renderer as the art director. First make a complete
portrait deck with the intended hierarchy, graphs, figures, real proof, logos,
and final key states. Approve the deck as static design. Then select the
lightest animation path that preserves it.

For each slide, record:

- the exact transcript range and duration
- the readable key state
- which elements enter, change, morph, or exit
- whether the slide is an opaque takeover or a source-preserving overlay
- the proof and face regions that may not be covered

## Route 1: Marp HTML

Prefer Marp's `bespoke` HTML presentation mode when the motion can be expressed
as slide-to-slide transitions, progressive list reveals, or duplicated-slide
morphs.

- Marp CLI supports fragmented lists, 33 built-in slide transitions, custom
  CSS transition keyframes, and element morphing through the browser View
  Transition API.
- Treat HTML playback as the motion authority. Marp does not provide a native
  MP4 export, so record the browser presentation deterministically at the
  delivery resolution and frame rate, then probe the captured file.
- Build motion as explicit intermediate slides when a figure needs multiple
  states. Use stable `view-transition-name` values only once per slide.
- Test the target browser first. Marp notes that morph behavior may differ by
  browser even when ordinary transitions work.
- Do not expect a normal Marp PPTX export to preserve editable object layers;
  it normally contains pre-rendered slide backgrounds. The experimental
  editable-PPTX option can reduce visual fidelity on complex themes.

Official references:

- [Marp CLI presentation features](https://github.com/marp-team/marp-cli#template)
- [Marp bespoke transitions and morphing](https://github.com/marp-team/marp-cli/blob/main/docs/bespoke-transitions/README.md)
- [Marp PPTX conversion limits](https://github.com/marp-team/marp-cli#convert-to-powerpoint-document---pptx)

## Route 2: Keynote on macOS

Prefer Keynote when the sequence needs richer object builds, action paths,
build-outs, or Magic Move-style continuity and the project can keep an
editable `.key` source.

- Reconstruct the selected slide as editable Keynote objects when internal
  object animation matters; importing a flat Marp slide image is not enough.
- Use Build In, Action, Build Out, and slide transitions intentionally. Avoid
  applying a different decorative effect to every object.
- Use a self-playing movie export. Keynote can advance builds and slides by
  timing, export a custom resolution and frame rate, and optionally export a
  transparent movie background.
- Validate one exact-duration portrait sample before converting the whole deck.
  Probe resolution, frame rate, duration, boundary frames, and alpha when used.

Official references:

- [Animate and transition in Keynote](https://support.apple.com/guide/keynote/get-started-with-keynote-tan115e144b4/mac)
- [Export a self-playing Keynote movie](https://support.apple.com/guide/keynote/tana0d19882a/mac)

## Route 3: PowerPoint

Use PowerPoint only when the operating-system export path has been proven for
the project.

- PowerPoint for Windows can export a video that includes animations,
  transitions, and recorded timings.
- Microsoft documents that PowerPoint for Mac movie export does not play
  animation effects and may render some transitions differently. Do not choose
  that path as the motion master on macOS.
- If Windows PowerPoint is available, test a portrait sample and verify that
  the requested custom dimensions, animations, fonts, media, and timings
  survive the video export before scaling up.

Official references:

- [PowerPoint for Windows video export](https://support.microsoft.com/en-us/powerpoint/turn-your-presentation-into-a-video)
- [PowerPoint for Mac movie-export limitations](https://support.microsoft.com/en-us/powerpoint/save-a-presentation-as-a-movie-file-or-mp4-in-powerpoint-for-mac)

## Route 4: Remotion or Manim

Use Remotion after deck approval when the work requires exact transcript
timebase control, alpha overlays, data-driven variants, native video
compositing, or reproducible batch output that slide-native tools cannot
provide. Use the approved slide as the visual specification and animate
semantic layers from it.

Use Manim when the explanation depends on exact semantic continuity across
equations, geometry, graphs, algorithms, or mechanisms. It may still inherit
the deck's typography, color, hierarchy, and poster state.

## Sample gate

Before a full batch, render one visually representative slide and one
source-preserving proof slide. Inspect first, middle, and final frames plus the
real A-roll composite. Record the renderer, source file, export settings,
elapsed time, output hash, and accepted limitations. Do not scale a route that
only preserved the static poster while producing weak or broken motion.
