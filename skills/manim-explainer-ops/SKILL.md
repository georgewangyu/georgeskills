---
name: manim-explainer-ops
description: Create precise programmatic explanatory animations with Manim Community Edition and hand editor-ready assets into a video workflow. Use for math, equations, machine-learning concepts, algorithms, data structures, graphs, geometric transformations, coordinate systems, causal mechanisms, and other explanations where semantic objects must transform with exact timing; keep UI, brand, and text-led motion on Remotion, and use Blender only after an explicit real-3D request.
---

# Manim Explainer Ops

Create one inspectable animation that makes a technical relationship easier to
understand. Preserve editable Python source, render deterministically, and
return assets with exact placement instructions.

## Route The Visual Job

Use the narrowest suitable lane:

| Lane | Use it for |
| --- | --- |
| Manim | Equations, graphs, coordinate systems, geometric transforms, algorithm state, tensors, model flow, and mechanisms whose meaning lives in precise object-to-object change |
| Remotion | UI, product flows, brand systems, typography, general text motion, screen-like composition, and whole-video assembly |
| Blender | Real 3D geometry, camera, lighting, depth, simulation, or reusable 3D scenes, only when the user explicitly requests Blender or bespoke 3D |
| Source proof | Real product behavior, benchmarks, articles, receipts, and claims that require evidence rather than illustration |

Do not use Manim merely because a beat mentions a number. Prefer a static
receipt, diagram, or A-roll when motion does not carry explanatory meaning.

## Lock The Explanation

Resolve before implementation:

- the exact concept and one-sentence teaching claim
- the narration beat and exact in/out duration
- the viewer's starting model and intended ending model
- the semantic objects that appear, change, and persist
- target aspect ratio, resolution, frame rate, background, safe zones, and
  whether the editor needs a full-frame clip or alpha-capable overlay
- required notation, labels, source data, and factual provenance
- the output directory and reserved filenames

Mark the animation as `explanation`, not `evidence`, unless every displayed
value comes from a cited source and the asset preserves that provenance.

## Build A Semantic Storyboard

Write first, middle, and final states. Give each scene one primary explanatory
change, such as:

- transform one equation into the next valid form
- map an input through an algorithm's current state to its output
- move a point while its coordinates, tangent, or loss value update
- reveal a graph, then isolate the relationship the narration names
- transform geometry while preserving the invariant being taught

Prefer semantic Manim objects and transformations over frame-by-frame
positioning. Keep labels short and visible at delivery size. Read
[manim-patterns.md](references/manim-patterns.md) for construct choices across
math, machine learning, algorithms, graphs, geometry, and mechanisms.

## Scaffold The Project

Create a clean project from the bundled template:

```bash
python3 <skill-dir>/scripts/scaffold_manim_project.py \
  --output <project-dir> \
  --project-name <slug> \
  --scene-class <SceneClass> \
  --title "<short title>"
```

The scaffold contains a pinned Manim Community Edition dependency, a vertical
editor-safe configuration, an editable scene, and a handoff manifest. It
refuses to write into a non-empty directory.

Use an isolated environment. Prefer `uv sync` and `uv run`; do not install or
upgrade Manim globally as a side effect of an animation task. Follow the
official Manim Community installation guide for system dependencies. Confirm
that the scene uses `from manim import ...`; examples written for ManimGL are
not interchangeable. If `import cairo` fails during a macOS bootstrap, read
[installation-troubleshooting.md](references/installation-troubleshooting.md)
and repair the isolated environment before rendering.

## Implement Precisely

1. Replace the scaffold's generic input-rule-output objects with the minimum
   semantic objects needed by the storyboard.
2. Keep timings explicit and aligned to the locked narration beat. Avoid
   unexplained magic constants when a named duration or layout token works.
3. Use equations and values truthfully. Derive displayed intermediate states
   from the same source data or calculation whenever practical.
4. Use one stable visual hierarchy: background, primary objects, secondary
   labels, and one meaningful accent.
5. Preserve object continuity with transforms when the viewer should understand
   that one state became another. Use cuts or replacement transforms when the
   identity genuinely changes.
6. Keep a readable poster frame. The animation should remain interpretable
   when paused at the key state.

Do not imitate 3Blue1Brown or another living creator's exact visual identity.
Use general explanatory mechanics such as semantic transforms, progressive
revelation, coordinate-linked motion, and invariant highlighting while choosing
an original palette, typography, pacing, composition, and narration structure.

## Render In Two Passes

Run a fast proof first:

```bash
cd <project-dir>
uv sync
uv run manim -ql -r 270,480 --fps 15 scene.py <SceneClass>
```

Inspect the first, middle, and final states against the storyboard and real
editor safe zones. Correct conceptual errors before polish. Then render the
delivery asset:

```bash
uv run manim -qh -r 1080,1920 --fps 30 scene.py <SceneClass>
```

Use a transparent render only when the receiving editor and codec path have
been tested. Composite a representative sample over the actual footage before
rendering a family of overlays.

## Verify And Hand Off

Probe the final media with the receiving workflow's asset inspector or
`ffprobe`. Verify duration, dimensions, frame rate, codec, blank frames,
legibility, safe margins, and narration sync. Inspect the actual first, middle,
and final frames; successful rendering alone is not visual QA.

Read [editor-handoff.md](references/editor-handoff.md), complete
`MANIM_HANDOFF.json`, and return:

- editable `scene.py`, `manim.cfg`, dependency file, and render command
- final MP4 or tested alpha-capable overlay
- PNG poster or representative frame
- exact timeline in/out and narration sync point
- dimensions, duration, frame rate, codec, and validation result
- source/provenance notes and `explanation` versus `evidence` classification
- explicit limitations, manual editor steps, and unresolved blockers

Register the outputs in the existing video asset manifest and return them to
the visual-director or editor workflow. This skill owns the specialist Manim
asset, not the whole edit, A-cut, or final publishing decision.

## Guardrails

- Do not fake product UI, benchmarks, receipts, or observed results.
- Do not hide a weak explanation behind decorative motion.
- Do not silently change notation, values, narration timing, or the factual
  claim to make the animation easier.
- Do not use Blender without the explicit 3D gate.
- Do not replace the default Remotion lane for UI, brand, or text motion.
- Do not copy private source media, local paths, credentials, or user-specific
  defaults into this public skill or generated examples.
