# Asset Manifest Schema

Create one `ASSET_MANIFEST.md` beside the assets.

## Required sections

### Claim-safe language

List corrected wording for history, rankings, pricing, live metrics, opinions, and disputed claims.

### Asset index

| # | Filename | Source | Claim supported | Capture state | Technical probe | Rights/provenance | Recommended use |
|---|---|---|---|---|---|---|---|

Use `capture state` values such as `static`, `captured <date/time>`, `mutable`, `generated`, or `unavailable`.
For motion and video assets, link the `inspect_asset_pack.py` probe output or
record codec, dimensions, duration, frame rate, audio streams, and rotation
directly. Do not infer these values from the extension or editor thumbnail.

### Spoken-beat map

For each beat include:

- spoken line or paraphrase
- selected asset and fallback
- treatment
- duration
- crop/highlight target
- caption qualifier

### Timed sequence

For short-form work, map the complete target duration. Prefer 1–3 second proof beats and alternate dense receipts with A-roll.

### Missing and richer visuals

Separate:

- required blocker
- optional pickup
- local prototype possible
- approval required for paid or synthetic generation

### Fast assembly notes

Tell the editor which assets to reuse with different crops, where metrics have changed, and what not to overstate.
