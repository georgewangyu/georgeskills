---
name: x-check-bird
description: "[DEPRECATED] Check X/Twitter using the legacy Bird CLI engine. Use ONLY as a fallback if the native xbot engine fails."
memory_tags:
  - domain:social-media
  - workflow:timeline-check
  - engine:bird-legacy
  - status:deprecated
---

# X Check Bird (Legacy - DEPRECATED)

> [!WARNING]
> This skill is deprecated. Please use **x-check-xbot** for all fresh X checks. This track is maintained for baseline comparisons only.

## Trigger

Use when:
- the user explicitly asks to use the "bird method"
- you need a ground-truth baseline to compare against the native engine
- the native xbot engine is experiencing issues

## Workflow

1. Use the stable private wrapper:
   - `python3 georgeskills/skills/exports-ops/scripts/export_x_feed_bird.py --only home`
2. Data is written to:
   - `notes-private/social-media/x/`
3. Summarize high-signal themes.
