# Creator Visual Style Profile

Use this schema when a creator has repeatable visual preferences. Keep the
profile creator-owned and, when appropriate, private. The reusable skill should
load the profile; it should not hardcode one creator's identity.

## Minimum Fields

```yaml
profile_id: creator-shortform-v1
status: pilot | active
canvas:
  width: 1080
  height: 1920
  fps: 30
safe_zones:
  title: {x: [90, 900], y: [140, 420]}
  captions: {x: [110, 890], y: [1370, 1570]}
  platform_exclusion: {bottom_px: 350, right_px: 150}
typography:
  title: {family: "...", fallback: "...", size_px: [86, 106]}
  captions: {family: "...", fallback: "...", size_px: [54, 64]}
  labels: {family: "...", fallback: "...", size_px: [28, 48]}
colors:
  primary_text: "#..."
  primary_surface: "#..."
  accent: "#..."
layout_rules: []
approved_recipes: []
series_presets: {}
```

## Runtime Rules

- Resolve font files or installed fallbacks before implementation. Never allow
  silent font substitution to change line wrapping.
- Treat template coordinates as guardrails. Face/action detection and the
  inspected composite override them.
- Record the profile path and version in the visual-edit plan.
- Separate stable creator defaults from project-specific reference mechanics.
- If a requested treatment conflicts with the profile, follow the creator's
  current request and record the exception instead of silently changing the
  profile.
- Add a preference only after explicit approval or repeated keep/remove
  evidence. Do not infer durable taste from one inspiration link.

## Project Override

Write project-specific decisions in `REFERENCE_TREATMENT.md` or
`VISUAL_DIRECTION.md`:

- chosen series preset
- exact title and caption treatment
- active colors
- face-safe anchor after inspecting the A-cut
- approved recipe budget
- borrowed reference mechanic and what is deliberately not copied
- any temporary exception to the creator profile
