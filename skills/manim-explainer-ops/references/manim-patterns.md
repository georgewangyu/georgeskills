# Manim Pattern Guide

Choose semantic objects that match the explanation. Prefer one meaningful
transformation over a collection of decorative animations.

| Domain | Useful Manim constructs | Typical explanatory change |
| --- | --- | --- |
| Equations | `MathTex`, `TransformMatchingTex`, braces, highlights | Preserve shared terms while one valid algebraic step changes |
| Functions and graphs | `Axes`, `NumberPlane`, `plot`, `ValueTracker`, `always_redraw` | Link a changing input to a point, slope, area, or output |
| Geometry | `Polygon`, `Circle`, `Line`, angle/length markers, transforms | Move or reshape objects while highlighting an invariant |
| Algorithms | Arrays of labeled shapes, pointers, edges, state panels | Advance one state transition and preserve already-settled state |
| Graphs and networks | `Graph`, vertices, edges, paths, color state | Reveal traversal, propagation, shortest path, or dependency flow |
| Machine learning | vectors, matrices, tensor blocks, axes, loss curves | Map input through layers, attention, embedding, gradient, or update |
| Mechanisms | labeled nodes, arrows, signals, counters, causal stages | Show what enters, what changes it, and what observable output follows |

## Precision Rules

- Derive displayed values from one source of truth when practical.
- Keep equations and notation consistent with the narration and source.
- Preserve object identity with matching transforms only when identity is real.
- Name timings and layout constants by semantic job.
- Keep critical labels inside the actual editor safe zone.
- Test LaTeX availability before depending on `MathTex`; a successful text-only
  smoke render does not prove the LaTeX toolchain.
- Use 3D Manim objects only for lightweight mathematical 3D. Route cinematic
  3D, lighting, camera, simulation, and reusable scenes to the explicit Blender
  lane.

## Originality Rule

Use general teaching mechanics: progressive revelation, object continuity,
coordinate-linked motion, invariant highlighting, and visualized state. Do not
copy a living creator's exact palette, typography, camera language, pacing,
scene composition, or signature transition system.
