# Editor Handoff

Complete `MOTION_HANDOFF.json` beside every final asset. Use one manifest per
independently movable clip or one array entry per clip in the parent asset
manifest.

## Required Fields

```json
{
  "asset_id": "07_queue-to-controller",
  "classification": "explanation",
  "visual_job": "Show scattered work becoming one managed queue",
  "narration_sync": {
    "timeline_in_seconds": 18.4,
    "timeline_out_seconds": 22.2,
    "spoken_cue": "one control layer",
    "handles_frames": 6
  },
  "delivery": {
    "mode": "alpha-overlay",
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "codec": "prores",
    "pixel_format": "record after probe",
    "audio_disposition": "silent-under-narration"
  },
  "placement": {
    "anchor": "full-canvas overlay",
    "scale": 1,
    "blend_or_composite_notes": []
  },
  "source": {
    "project": "./src",
    "render_command": "record exact command",
    "provenance": []
  },
  "artifacts": {
    "final_clip": "outputs/alpha.mov",
    "review_clip": "outputs/review.mp4",
    "poster": "outputs/poster.png",
    "sampled_frames": {
      "first": "outputs/qa/first.png",
      "transformation": "outputs/qa/transformation.png",
      "final": "outputs/qa/final.png"
    },
    "contact_sheet": "outputs/qa/contact-sheet.png",
    "validation_receipt": "outputs/qa/validation.json"
  },
  "approval": {
    "poster_frame": 72,
    "poster_approved": false,
    "approved_by": null
  },
  "validation": {
    "first_transformation_final_inspected": false,
    "phone_scale_checked": false,
    "real_composite_checked": false,
    "safe_zones_checked": false,
    "cut_boundaries_checked": false,
    "adjacent_mechanics_checked": false
  },
  "receiving_editor": {
    "import_test_status": "not-run",
    "import_notes": []
  },
  "editor_notes": [],
  "known_limits": []
}
```

## Delivery Rules

- Default assets to video-only and `silent-under-narration`. Add SFX only when
  the work order assigns audio ownership and gives an exact cue.
- Preserve an ordinary review render even when the final delivery uses alpha.
- Record exact timeline placement; filenames or asset order are not sufficient.
- Probe the delivered file and replace planned codec and pixel-format values
  with observed values.
- Keep each requested editor asset separately movable, disableable, and
  replaceable. Do not substitute one full-duration finishing layer.
- Return first, transformation, poster, and final frames or a contact sheet so
  the editor can identify the clip without opening the source project.
- Treat the scaffold artifact paths as reserved output locations. Fill them,
  change them to the actual paths, or mark them explicitly unavailable before
  handoff; never leave a path implying an artifact that was not produced.
- Record the receiving editor's import result and any alpha-interpretation,
  scaling, safe-zone, or placement adjustments under `receiving_editor`.
