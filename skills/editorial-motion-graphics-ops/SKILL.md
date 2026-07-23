---
name: editorial-motion-graphics-ops
description: Design and render selected premium editorial motion sequences as individual editor-ready assets. Use for kinetic typography, conceptual UI or card motion, gauges, cascades, focus pulls, depth changes, shared-object transitions, state changes, and coded morph-like sequences that must explain a narration beat with exact timing. Use after a visual director or asset router selects the beat; do not use for whole-edit orchestration, source-proof acquisition, sketch-style social loops, or precise mathematical and algorithmic semantic transformations.
metadata:
  memory_tags:
    - domain:social-media
    - workflow:editorial-motion-graphics
    - skill_role:generator
    - inputs:narration-beat
    - outputs:editor-ready-motion-asset
    - repo_boundary:tools
    - risk:medium
---

# Editorial Motion Graphics Ops

Create one authored motion sequence that makes an idea physical. Return a
reproducible source project, a strong poster frame, an editor-safe render, and
an exact placement manifest. Own the selected sequence, not the surrounding
edit.

## Operating Boundary

- Let `video-visual-director-ops` own the locked A-cut, whole-edit rhythm,
  visual system, CapCut or other editor integration, and final acceptance.
- Let `video-visual-assets-ops` rank selected asset opportunities and route
  proof, generated media, screen demonstrations, diagrams, and specialist
  production paths.
- Use `manim-explainer-ops` when meaning depends on exact equation, graph,
  coordinate, geometry, algorithm, or mechanism transformations.
- Use `social-motion-diagram-ops` for sketch-style, mostly static social
  diagrams with one small looping motion cue.
- Keep this skill on premium editorial motion: kinetic type, conceptual UI,
  cards, gauges, cascades, focus and depth, shared-element continuity, and
  data-driven state changes.

## Do Not Use This Skill

Do not use it when a screenshot, receipt, A-roll hold, or static diagram
already performs the job; when the request is for an entire video treatment;
when the asset must prove real product behavior or an external claim; when a
precise technical transform belongs in Manim; or when a lightweight sketch
loop is the desired visual grammar. Do not animate merely to increase activity.

## Input Gate

Resolve before design:

- the exact narration beat, timeline in/out, spoken sync phrase, and one visual
  job: `explain`, `compress`, `compare`, `transition`, or `punctuate`
- the physical metaphor and the belief or state that must change
- target width, height, frame rate, safe zones, and phone review size
- project art direction: fonts, palette, hierarchy, texture, and motion tone
- persistent caption, title, face, hand, proof, and platform-exclusion regions
- `alpha-overlay` or `full-screen`, required handles, codec, and receiving
  editor
- audio disposition: normally `silent-under-narration`; otherwise exact SFX or
  designed-audio ownership
- output directory, reserved asset id, and source/provenance classification

If the sequence has no explanatory or editorial job, return a static treatment
or no asset instead.

## Design The Sequence

### 1. Translate narration into a physical metaphor

Write one sentence in the form: `<objects> physically <verb>, so the viewer
feels or understands <claim>`. Prefer verbs such as crowd, drain, narrow,
split, queue, orbit, fold, hand off, focus, collapse, or resolve. Avoid a stack
of headings that merely restates the narration.

Read [motion-design-playbook.md](references/motion-design-playbook.md) when
choosing metaphors, continuity objects, kinetic-type behavior, gauges,
cascades, or focus pulls.

### 2. Lock first, transformation, and final states

Define three inspectable key states before coding:

1. `first`: establish objects, hierarchy, and viewer model.
2. `transformation`: show the causal or editorial change.
3. `final`: land the new state and the narration's conclusion.

Name the shared objects and record how their geometry, role, or emphasis
changes. Do not make three disconnected slides when the viewer should
understand that one object became another.

Create the intended poster frame at delivery aspect ratio and obtain visual-
direction approval before full animation. Treat poster approval as a blocking
gate for a batch or any sequence with material art-direction judgment. Motion
cannot rescue weak hierarchy, generic cards, bad line breaks, or an incoherent
palette.

### 3. Route the engine by the job

Use the smallest engine that preserves the approved states and delivery
contract. Remotion is the default deterministic lane for exact frame timing,
alpha, reusable coded components, and data-driven variants; it is not a
permanent requirement.

| Job | Preferred lane |
| --- | --- |
| Exact editorial choreography, alpha, variants, UI, type, gauges, cards | Remotion or equivalent frame-driven code |
| Two or three approved slide-like states with human-editable object moves | Keynote or another proven slide-native motion tool |
| Lightweight portable vector overlay | SVG/HTML/CSS/canvas browser capture |
| Equations, graphs, coordinates, geometry, algorithms, exact mechanisms | `manim-explainer-ops` |
| Sketch-like static diagram with minimal loop | `social-motion-diagram-ops` |
| Product truth, benchmark, article, or observed behavior | Source-faithful proof, not illustrative motion |

Read [engine-routing.md](references/engine-routing.md) for the full decision
table, proof requirements, and failure gates.

### 4. Build deterministic motion

- Convert seconds to frames once. Keep timings in a spec or named constants,
  not scattered literals.
- Use clamped progress functions, custom easing, controlled springs, stagger,
  masked text, SVG geometry, and coordinate interpolation deliberately.
- Use blur, scale, velocity, occlusion, and depth to encode focus or state;
  never blur required text or proof.
- Keep ambient motion deterministic and subordinate. Avoid unseeded randomness,
  autoplay clocks, or CSS timing that diverges from the render frame.
- Preserve shared objects across states. Interpolate geometry or pass stable
  identifiers through transitions instead of fading out one slide and fading
  in another.
- Make the first and last frames usable as hard cuts unless the edit plan
  explicitly requires handles or a transition dependency.
- Keep critical type inside the resolved safe zones and readable at the phone
  review size. Do not rely on the isolated asset when the real composite has a
  face, hands, captions, or persistent title.
- Use one coherent hierarchy and a small motion vocabulary. Animation must
  explain, prove a relationship, or land a phrase; decoration is insufficient.

For a new Remotion-based project, scaffold the reusable starter:

```bash
python3 <skill-dir>/scripts/scaffold_editorial_motion_project.py \
  --output <project-dir> \
  --project-name <slug> \
  --title "<short final-state title>" \
  --duration-seconds <seconds> \
  --delivery-mode <alpha-overlay|full-screen>
```

The scaffold is an editable technique sample, not an art-direction preset.
Replace its generic copy, objects, palette, and composition with the approved
key states. It pins Remotion and `@remotion/google-fonts`; the first install or
render needs network access to fetch exact-version packages and versioned font
files. For an offline or archival pipeline, vendor approved redistributable
fonts into the project and load them locally before poster approval. The
bundled starter uses a scalable 9:16 design space; for another
aspect ratio, follow the same state and handoff contracts but redesign the
composition rather than stretching it. Reuse an existing compatible Remotion runtime when the invoking
workflow provides one; otherwise install the scaffold's pinned project
dependencies in isolation.

### 5. Earn the delivery mode

Choose `alpha-overlay` when the speaker or source footage must remain the
authenticity layer and the motion can perform its job without replacing the
canvas. Composite one representative proof over the real footage before
rendering a family.

Choose `full-screen` only when phone legibility, a conceptual transformation,
or a meaningful multi-state sequence needs the whole canvas. A still card,
single scale loop, or decorative title does not earn a takeover. Keep the
sequence no longer than the visual job requires and return cleanly to A-roll.

### 6. Render proof before delivery

Render the poster and one short proof at reduced scale or resolution. Inspect
first, transformation, and final frames before the delivery render. For a
family, approve one representative overlay composite and one representative
full-screen sequence before the batch.

Then render the exact requested asset with handles. Keep alpha assets video-
only unless audio is explicitly part of the work order. Never assume an alpha
codec works in the receiving editor; test the pixel format and a real
composite.

## Verify

Read [qa-rubric.md](references/qa-rubric.md), then:

1. Probe duration, dimensions, frame rate, codec, pixel format, rotation, and
   audio streams.
2. Inspect the actual first, transformation, poster, and final frames.
3. Review at phone scale and over real footage when the asset is an overlay.
4. Check face, hand, caption, title, proof, and platform-safe collisions.
5. Build a contact sheet for the sequence and a cadence contact sheet for a
   family or full edit.
6. Flag adjacent sequences that repeat the same primary mechanic, composition,
   or arrival behavior.
7. Verify every displayed claim and classify the asset as `explanation`,
   `synthetic-illustration`, or `evidence` with provenance.
8. Confirm the first and final frames are cut-safe and the visual remains
   coherent with sound off.

Rendering success is not visual QA. Fix legibility, hierarchy, continuity,
timing, or technical defects before optional polish.

## Handoff

Read [editor-handoff.md](references/editor-handoff.md) and return:

- approved key-state board or poster and approval status
- editable source and reproducible render command
- final clip plus tested poster or representative frames
- exact timeline in/out, handles, narration cue, and placement geometry
- alpha or full-screen classification and editor import notes
- audio disposition and any exact SFX cue
- duration, dimensions, frame rate, codec, pixel format, and validation receipt
- provenance and `explanation`, `synthetic-illustration`, or `evidence` label
- known limitations, manual steps, and unresolved collisions or taste risks

Register each clip as an individual asset in the parent manifest. Do not return
a baked whole-edit layer when the work order asks for independently movable,
disableable, or replaceable editor assets.

## Guardrails

- Do not fabricate product UI, receipts, benchmarks, articles, or observed
  results.
- Do not imitate a living creator's exact visual identity. Borrow portable
  mechanics and rebuild them inside the project's own art direction.
- Do not hardcode private paths, people, palettes, footage, accounts, or
  creator defaults into this reusable skill or scaffold.
- Do not silently change narration, facts, timecodes, safe zones, delivery
  mode, or audio ownership to simplify the render.
- Do not let expensive custom motion block a usable first edit; prove the
  representative sequence before scaling.
