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
  "style_profile": {
    "path": "/absolute/path/creator-shortform-style.md",
    "version": "0.1-pilot",
    "preset": "series-name",
    "exceptions": []
  },
  "delivery_mode": "native_editor_timeline",
  "editability_target": {
    "editor": "CapCut",
    "required": true,
    "editable_layers": ["a_roll", "titles", "proof", "motion", "captions"],
    "review_export_source": "declared editor project"
  },
  "render_strategy": {
    "preflight_report": "plan/RENDER_PREFLIGHT.md",
    "sample_seconds": 8,
    "projected_full_render_seconds": null,
    "retry_budget": 1
  },
  "mechanic_budget": 1,
  "visual_rules": ["proof-first", "restrained punch-ins"],
  "supplied_asset_inventory": "plan/SUPPLIED_ASSETS.md",
  "srt_sync_status": "spot_checked",
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
