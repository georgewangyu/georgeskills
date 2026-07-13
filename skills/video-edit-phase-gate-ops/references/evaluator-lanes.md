# Evaluator Lanes

Use the same exact render and requirements ledger for every lane. Evaluators
are read-only and return one verdict: `PASS`, `FAIL`, or `BLOCKED`.

## Mandatory Trigger Matrix

Run all three independent lanes when any condition is true:

- sponsor, brand-deal, or product-demo footage is present
- creator-supplied proof or an exact evidence asset is required
- the video is at least 45 seconds or contains eight or more prepared assets
- the edit has already failed one correction or replacement cycle
- text, proof, sound cues, and editor persistence must all be reconciled

For a small low-risk edit, the parent may combine the lanes in one documented
pass. Never skip rendered inspection merely because the project is small.

## Lane 1: Content And Text

Inputs: render, transcript, intake ledger, canonical text map, asset manifest,
and accepted discrepancies.

Check:

- every required amount, category, label, CTA, and supplied asset appears
- exact wording, spelling, reveal order, semantic grouping, and timing
- independent narrated categories remain separate
- visible evidence matches the claim or the discrepancy is explicitly accepted
- no requirement is satisfied only in metadata but absent from the render

Return exact timestamps and the expected versus observed value for each failure.

## Lane 2: Visual And Brand

Inputs: render, visual plan, safe zones, asset manifest, and source references.

Check:

- assembled face, caption, proof-text, and platform-safe zones
- framing mode, crop, scale, legibility, visual usefulness, and takeover reason
- first, middle, and final frames of every motion or product-demo asset
- product-only purity when required: correct UI/action, no unrelated person,
  room, creator branding, filler, or conflicting baked captions
- blank, black, dim, reset, corrupt-alpha, or one-frame transition defects

Use `video-visual-coverage-qa-ops` for timestamped visual inspection.

## Lane 3: Technical, Audio, And Persistence

Inputs: render, A-cut identity, sound cue map, editor lineage, media inventory,
and persistence evidence.

Check:

- duration, aspect ratio, resolution, frame rate, missing media, and sync
- narration continuity and whether new gaps were introduced
- every required SFX cue is audible, correctly timed, and does not mask speech
- planned cue count equals assembled cue count equals audibly verified cue
  count, excluding only ledgered `intentionally silent` cues
- project changes survive reopen/resave and all required graph copies agree
- the exported render came from the exact declared project version
- the declared delivery mode and required editable layers match Phase 0
- required native tracks and materials exist when native editability was
  requested; loose files and instructions do not count
- before/after track counts, media references, close/reopen/resave read-back,
  and export provenance support the persistence claim
- final and source fingerprints match the acceptance report

Track presence is not proof of audible output; project JSON is not proof of
rendered pixels.

## Optional Taste Lane

Check pacing, energy, novelty, visual rhythm, and whether the treatment feels
strong enough. Classify findings as `optional_taste` unless they create a clear
comprehension, factual, or accessibility defect.

## Verdict Contract

Each lane returns:

1. verdict
2. inputs and fingerprints inspected
3. required findings with timestamps and evidence
4. high-leverage improvements
5. optional taste notes
6. exact rerender scope needed after fixes

The parent may deduplicate reports but must preserve the strongest severity and
the underlying evidence.
