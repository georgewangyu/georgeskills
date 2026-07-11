# Visual Edit Plan Schema

Use one project header and one entry per meaningful timed beat. JSON is preferred for Remotion execution; Markdown is acceptable for planning if every field remains explicit.

## Project Header

```json
{
  "project": "2026-07-10_example-video",
  "a_cut": {
    "path": "/absolute/path/a_cut_v03.mp4",
    "sha256": "...",
    "bytes": 12345678,
    "duration_seconds": 42.18,
    "fps": 30
  },
  "canvas": {"width": 1080, "height": 1920},
  "delivery_mode": "full_composite",
  "visual_rules": ["proof-first", "restrained punch-ins"],
  "beats": []
}
```

## Beat Entry

```json
{
  "id": "beat-04",
  "in_seconds": 8.4,
  "out_seconds": 12.1,
  "transcript": "Independent testing placed it near the top.",
  "primary_job": "proof",
  "treatment": "Benchmark receipt slides behind a masked A-roll cutout, then resolves full-screen.",
  "a_roll": {"scale_from": 1.0, "scale_to": 1.07, "anchor": "face"},
  "asset": {"path": "assets/07_benchmark.png", "source_url": "https://..."},
  "audio": {"sfx": "soft-whoosh", "music_sync": false},
  "execution": "remotion_sequence",
  "priority": "required",
  "confidence": "high",
  "rationale": "The spoken claim needs visible evidence.",
  "qa": ["benchmark label readable on phone", "face not obscured"]
}
```

## Allowed Primary Jobs

- `a_roll_only`
- `a_roll_emphasis`
- `proof`
- `context_broll`
- `text_compression`
- `mechanism_motion`
- `transition_reset`

Every beat needs one primary job even if it contains several layers. Mark proof and legibility needs as `required`; mark style experiments as `optional`.
