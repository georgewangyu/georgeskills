# Motion Design Playbook

## Physical Metaphors

| Narration idea | Physical treatment | Continuity object |
| --- | --- | --- |
| Too many demands | Cards crowd the frame, accelerate, and reduce negative space | The same cards later queue or collapse |
| Capacity falls | A ring, aperture, or lane count drains while motion slows | One gauge geometry persists across states |
| Work becomes parallel | One path splits into synchronized paths with a shared origin | The original path remains visible through the split |
| Delegation or handoff | Scattered objects fold into a controller, container, or spine | Object edges become the container geometry |
| Focus or bottleneck | Surrounding objects blur or streak while the focal object remains sharp | The focal object persists while depth changes |
| Simplification | Many controls resolve into one portal while status marks continue | The container expands rather than being replaced |
| Choice | One object forks into two tactile states without preselecting an answer | The divider grows from the original object |

Prefer one physical verb per beat. Combine verbs only when the narration names
a causal chain.

## Key-State Contract

For each state, record:

- frame or normalized progress
- dominant object and one-sentence viewer interpretation
- exact visible copy and maximum simultaneous readable words
- object ids that persist from the prior state
- geometry, color, focus, or role changes
- face, caption, title, proof, and platform exclusions
- whether the state is a cut-safe boundary or an internal transition

Choose the poster from a useful comprehension state, not automatically frame
zero. Approve hierarchy, line breaks, contrast, and composition before motion.

## Deterministic Techniques

- Create a clamped `progress(frame, from, to, easing)` helper.
- Keep the project timebase and event timings in one data object.
- Use custom cubic curves for departures and arrivals; reserve springs for
  tactile settling, not every transition.
- Stagger by semantic order. Do not stagger unrelated objects merely because a
  loop is easy to write.
- Reveal type with clipping masks, line masks, or per-word/per-character motion
  tied to the spoken phrase.
- Interpolate shared-object coordinates, dimensions, radii, path points, and
  colors from one state to the next.
- Use SVG paths and dash offsets for routes, gauges, or causal connections.
- Encode focus with controlled blur, contrast, scale, depth, and velocity while
  protecting required copy.
- Drive ambient particles, scan lines, or glow from frame math and fixed data.
  Keep them quiet enough that the main state change remains obvious.

## Art-Direction Rules

- Establish one type hierarchy, one spacing system, and a small accent palette.
- Use a dominant composition, not an interchangeable dashboard of small cards.
- Keep conceptual UI clearly illustrative. Do not mimic a real product unless
  the source is genuine and provenance is preserved.
- Use full-screen darkness, texture, grain, and glow only when they support the
  concept or focus hierarchy.
- Keep every sequence interpretable with sound off, but do not duplicate full
  captions as graphics.
- Vary mechanics across adjacent sequences while preserving the same visual
  language. Repetition should feel like a motif, not a template factory.
