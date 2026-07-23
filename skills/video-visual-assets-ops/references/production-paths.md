# Visual Production Paths

## Selection table

| Path | Best for | Default output | Approval |
|---|---|---|---|
| Screen recording | Real product behavior or UI flow | MP4 + poster | No, when access is already available |
| Official promo excerpt | Product launch, cinematic context, physical behavior | Short MP4 + provenance | Ask before large downloads; otherwise no |
| Manim explainer | Equations, graphs, coordinates, geometry, machine-learning flow, algorithm state, precise mechanisms | MP4 + PNG + editable Python source | No |
| Editorial motion specialist | Premium kinetic type, conceptual UI/cards, gauges, cascades, focus/depth, shared-object state changes | MP4 or tested alpha clip + PNG + editable source + placement manifest | No |
| Diagram/board | Systems, contrasts, agent delegation, before/after | PNG or short MP4 | No |
| Generated still | Atmosphere, metaphor, comedic plate, impossible B-roll | PNG | Ask if billable |
| Generated video | High-novelty transitions, impossible scenes, stylized B-roll | MP4 | Explicit approval |
| Blender 3D | Bespoke geometry, controllable camera/depth/lighting, reusable 3D scenes | MP4 + `.blend` source + poster | Explicit Blender/Blender MCP/3D request |

## Screen recording

Use real UI and a short, deterministic interaction. Hide private data, notifications, tokens, and unrelated tabs. Capture only the interaction needed for the spoken beat.

## Official promo excerpt

Prefer official press kits, launch posts, product sites, or channels owned by the subject. Record URL, owner, original duration, excerpt boundaries, and intended editorial transformation. Avoid rehosting whole promotional videos.

## Manim explainer

Invoke `manim-explainer-ops` when the teaching value depends on exact semantic
object transformations: equations becoming equations, points linked to graph
values, geometry preserving an invariant, algorithm state advancing, or a
mechanism mapping input to output. Keep the Python source and classify the
result as explanation rather than proof unless sourced values justify an
evidence label. Borrow general teaching mechanics, not a living creator's exact
visual identity.

## Editorial motion specialist

Invoke `editorial-motion-graphics-ops` for selected premium UI, brand,
typography, card, gauge, cascade, focus/depth, and shared-object sequences.
Define and approve first, transformation, and final states before animation.
Let the specialist choose Remotion, a proven slide-native path, or deterministic
browser motion according to timing, alpha, editability, and state-continuity
requirements. Return an individual editor asset, poster, editable source,
reproducible render command, and exact placement manifest.

## Diagram or comparison board

Use when two or more objects must be compared at once or a process has several dependent steps. Make the still frame useful before adding motion.

## Generated still

Use for metaphor, mood, humor, or a non-factual transition. Do not recreate a real screenshot or imply documentary evidence. Preserve the prompt and mark it generated in the manifest.

## Generated video

Use only when motion itself carries enough value to justify cost and latency. Write a shot-level prompt, target 2–5 seconds, generate the minimum number of variants, and label synthetic footage. Never use it to impersonate a real event or fake product behavior.

## Blender 3D

Use only when the creator explicitly asks for Blender, Blender MCP, or a
bespoke 3D treatment. Do not select it from a generic request for fancy B-roll,
cinematic polish, or animation. Prefer generated video for fast cinematic
inserts and coded motion for exact explanatory graphics. Choose Blender when
the shot specifically benefits from editable geometry, camera control,
lighting, simulation, depth, or a reusable scene. Produce a low-resolution
proof first, preserve the `.blend` source, and classify the render as
synthetic illustration rather than evidence.

## Verification checklist

- correct aspect ratio and safe margins
- legible at phone scale
- first/middle/final frames inspected
- duration and frame rate verified
- no private data or accidental browser chrome
- provenance recorded
- synthetic status recorded
- exact narration sync point documented
