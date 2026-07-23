# Editorial Motion QA Rubric

Judge rendered pixels, narration, art direction, and the receiving composite
together. A passing render command is only a technical precondition.

| Axis | Pass evidence | Reject or revise when |
| --- | --- | --- |
| Visual job | The transformation explains, compresses, compares, transitions, or punctuates the exact beat | Motion merely decorates or repeats the spoken words |
| Key states | First, transformation, and final states are readable and share intentional objects | States feel like disconnected slides or the final belief is unclear |
| Poster | Approved frame has deliberate hierarchy, line breaks, contrast, and composition | Motion is being used to hide a weak static design |
| Timing | Frame boundaries match the narration and handles; first and last frames are cut-safe | Empty first frame, late reveal, fade from black, reset, or asset shorter than placement |
| Phone legibility | Critical copy and state change remain clear at a 360x640 or equivalent proxy | Text, UI, or proof requires pausing or zooming |
| Composite safety | Real-footage sample clears faces, hands, captions, title, proof, and platform exclusions | The isolated asset passes but the assembled frame collides |
| Continuity | Shared objects retain identity through geometry, focus, role, or color changes | Objects disappear and unrelated replacements arrive without meaning |
| Motion feel | Easing, spring, stagger, depth, and ambient movement serve hierarchy | Linear drift, bounce-heavy presets, simultaneous animation, or uncontrolled noise dominates |
| Art direction | Type, palette, spacing, texture, and mechanics form one system | Generic UI cards, random accents, or unrelated visual languages accumulate |
| Cadence | Contact sheet shows intentional quiet and varied primary mechanics | Adjacent assets repeat the same layout, reveal, scale loop, or full-screen takeover |
| Truth | Claims, values, product UI, and evidence preserve provenance and classification | Illustration impersonates a receipt, benchmark, real interface, or observed result |
| Technical | Probe confirms requested dimensions, duration, frame rate, codec, pixel format, alpha, rotation, and audio | Metadata or real editor behavior contradicts the handoff |

## Minimum Sampling

- frame zero and first usable frame
- midpoint of the transformation
- intended poster frame
- final usable frame and last frame
- one frame before and after every edit boundary
- dense samples around fast masks, blur changes, alpha edges, and object handoffs

For a family, create one contact sheet ordered by timeline. Label each asset's
primary mechanic and flag adjacent repetition. For a whole-edit cadence sheet,
include the underlying A-roll or scene context; transparent pixels alone cannot
prove face safety or rhythm.
