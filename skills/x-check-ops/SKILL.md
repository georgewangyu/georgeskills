---
name: x-check-ops
description: Check X/Twitter using the local export pipeline. Use for home-feed pulls, timeline checks, search exports, one-post reads, and "anything interesting?" scans.
memory_tags:
  - domain:social-media
  - workflow:timeline-check
  - repo_boundary:tools
  - data_class:private-derived
  - inputs:web
  - outputs:status-report
  - platform:x-twitter
  - risk:high
---

# X Check Ops

## Trigger

Use when:
- the user says `check X`, `check Twitter`, `check my feed`, or `what's interesting on X`
- the user wants a fresh home-feed pull, a search export, or a one-post read
- the task is about scanning private X/Twitter exports for themes or notable posts

Do not use when:
- the task is generic browser automation with no X-specific export need
- the user needs a UI-debugging browser flow; use `playwright`
- the task spans multiple export domains at once; use `exports-ops`

## Inputs

- Optional: export mode (`home`, `bookmarks`, `likes`, `search`, `read`)
- Optional: search query, count override, specific post URL or tweet id

## Workflow

1. Use the stable private wrapper in `<private-repo>`:
   - `python3 scripts/exports/social-media/export_x_feed_bird.py --check-auth`
   - `python3 scripts/exports/social-media/export_x_feed_bird.py --only home`
2. If the user wants search or a direct post read:
   - `--search "<query>" --search-count <n>`
   - `--read <tweet-id-or-url>`
3. Read the newest export under:
   - `notes-private/social-media/x/`
4. Summarize repeated themes, notable posts, and whether the feed is mostly noise or actually useful.

## Output Contract

- whether auth worked
- what was exported
- where the fresh snapshot was written
- 2-5 high-signal themes or posts
- any blocker such as auth failure or missing local config

## Guardrails

- Treat X exports as private derived data.
- Use the private wrapper path, not hardcoded personal token values.
- Do not claim trend significance from one noisy snapshot without saying it is a single-feed read.
