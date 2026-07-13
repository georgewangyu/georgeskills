# Render Fast Path

Use this gate before any full-duration composite or transparent-overlay render.

## Declare The Delivery

Choose the lightest artifact that satisfies the editability requirement:

- Native editor timeline: render only custom motion assets, then assemble them
  in the named editor project.
- Individual editor assets: render only the occupied beat windows with short
  handles; do not render a transparent track for the entire A-cut.
- Full composite: use only when the treatment truly changes the A-roll canvas
  or the user asks for a baked result.

## Preflight

Record the exact binaries and runtime paths. Verify:

On Apple Silicon, prefer an `arm64` FFmpeg binary such as
`/opt/homebrew/bin/ffmpeg` and its matching `ffprobe`. Do not trust PATH when an
older Intel Homebrew prefix may come first. Confirm architecture with `file`.

1. Input decode, dimensions, duration, frame rate, audio streams, and rotation.
2. Required FFmpeg filters, encoders, alpha pixel format, and hardware encoder.
3. Remotion dependency resolution and public-asset behavior from the shared
   runtime without project-local `node_modules` or duplicated source media.
4. One first, middle, and final representative frame.
5. One representative `5-10s` render sample with wall-clock time.

When assembling a short overlay sample with FFmpeg at a nonzero timeline
position, offset the overlay input itself (for example,
`setpts=PTS+START/TB`) before `overlay=enable=...`. An `enable` window alone
does not retime a short input, so the asset can decode and end before its
intended beat. Inspect a frame near the overlay's start, middle, and end to
catch this failure before approving the sample.

Do not begin the full render until the sample passes. Project the total time
from the sample. If the estimate is poor, change the pipeline before spending
the full-duration cost.

## Fast Assembly Order

Prefer, in order:

1. Native editor assembly from independently produced assets.
2. Short per-beat opaque or alpha clips rendered concurrently, then placed in
   the editor.
3. Frame-counted FFmpeg segments with hardware encoding, concatenated once,
   then original audio remuxed without re-encoding.
4. A full Remotion A-roll composite only after its sample benchmark proves it
   is reasonable.

Avoid a full-duration alpha render when most frames are empty. Avoid an FFmpeg
graph that evaluates disabled overlays on every frame. Avoid re-encoding audio
or unchanged video more than once.

## Retry Budget

Allow one corrected retry per render strategy. After two failures or a sample
that projects beyond the task's time budget, stop that path, preserve the logs,
and switch strategies. Parallelize proof acquisition, motion-asset generation,
caption/text preparation, and QA fixtures; keep final timeline mutation and
the shared timebase under one integrator.

Record selected strategy, sample timing, projected duration, actual duration,
failed paths, and reusable learning in `RENDER_PREFLIGHT.md` or the project's
equivalent plan artifact.
