---
name: youtube-check-ops
description: Check a YouTube channel or video for public metadata, preferring lightweight probes before browser viewing.
memory_tags:
  - domain:social-media
  - workflow:account-check
  - skill_role:researcher
  - repo_boundary:tools
  - inputs:web
  - outputs:status-report
  - risk:low
---

# YouTube Check Ops

## Trigger

Use when:
- the user wants to check a YouTube channel, handle, or public video
- the user asks to inspect a YouTube handle or channel
- the task needs a quick channel metadata read before any browser fallback

Do not use when:
- the task is video transcription; use `youtube-transcribe-ops`
- the task is general browser automation with no YouTube-specific logic
- the user needs Studio/private account access

## Inputs

- Required: YouTube handle, channel URL, or video URL
- Optional: whether API credentials already exist, whether browser viewing is allowed

## Workflow

1. Normalize the target:
   - handle like `examplecreator`
   - channel URL like `https://www.youtube.com/@examplecreator`
2. Run the local probe:
   - `skills/youtube-check-ops/scripts/check_youtube_target.sh <target>`
3. Interpret the result:
   - channel title and description are usually available from public metadata
   - subscriber counts may appear in page text but can be rounded
4. Decide access path:
   - if the user already has API credentials and needs structured channel data, read `references/current-options.md`
   - otherwise the public page is usually enough
   - use `playwright` only for visual confirmation or deeper browsing

## Output Contract

- normalized target
- whether the first-party YouTube URL appears reachable
- any public channel metadata extracted from the page
- recommended next path: API, public probe, or browser viewing

## Guardrails

- Prefer official YouTube Data API only when credentials are already available.
- Treat regex matches in public page text as best-effort.
- Do not use browser automation unless it adds value beyond public metadata.

## References

Open only when needed:
- current API and extraction caveats: `references/current-options.md`
