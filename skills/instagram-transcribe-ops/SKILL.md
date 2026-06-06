---
name: instagram-transcribe-ops
description: Transcribe an Instagram Reel or video post to text, preferring subtitles before local audio fallback.
memory_tags:
  - domain:social-media
  - workflow:transcription
  - repo_boundary:tools
  - inputs:web
  - outputs:transcript
  - risk:medium
---

# Instagram Transcribe Ops

Use when the user wants a transcript of an Instagram Reel or video post.

## Goal

Produce the best available transcript for an Instagram Reel or video URL with a CLI-first workflow. Do not use browser automation by default, but allow screen-control fallback when the user asks for it or CLI extraction is blocked.

## Workflow

1. Confirm the target is an Instagram Reel or video URL.
2. Run the shared social transcription helper.
3. Prefer subtitle extraction when available.
4. Fall back to local audio transcription when subtitles are unavailable.
5. If CLI extraction cannot access the video and browser fallback is allowed, use the browser fallback rules below.
6. Clean the transcript and return a concise confidence note describing the extraction path used.

## Preferred Order

1. Platform-provided subtitle tracks fetched by CLI.
2. Local audio extraction plus Whisper transcription as fallback.
3. Browser-assisted capture only when CLI paths fail or the user explicitly asks to use their browser session.

## Inputs

- Instagram Reel or video URL
- Optional output preference:
  - plain transcript
  - timestamps
  - cleaned summary plus transcript

## Extraction Rules

- Prefer the least invasive path that yields usable text.
- Treat post descriptions as supporting context, not as the transcript, unless the user explicitly asks for all visible text.
- If only partial on-screen captions are available, say that the result is partial before falling back to audio transcription.
- Preserve speaker boundaries when clearly detectable.

## Audio Fallback

If captions are unavailable or incomplete:

1. Download or otherwise acquire the video/audio with `yt-dlp`.
2. Extract audio to a local temporary file.
3. Transcribe with the local Whisper path already used in other transcription workflows.
4. Clean obvious filler artifacts only when they are clearly transcription noise.

## Browser Fallback

If CLI/subtitle/audio acquisition is blocked:

1. Prefer `playwright` for public/clean-session viewing.
2. Use `social-screen-control-ops` when the user explicitly wants Codex screen control, logged-in local browser state is needed, or Playwright/public probes are blocked or flaky.
3. Keep media muted unless audio capture/listening is required for transcription and the user has approved that.
4. Capture only what is needed for transcription: visible captions, post text, page state, or a locally acquired media/audio artifact.
5. Do not send DMs, post, comment, like, follow, change account settings, solve captchas, or enter credentials unless the user gives explicit task-specific approval at action time.

## Local Helper

Primary entrypoint:

```bash
python3 <georgeskills-root>/scripts/social_transcribe.py --platform instagram --url "<instagram-reel-url>"
```

Optional flags:

```bash
python3 <georgeskills-root>/scripts/social_transcribe.py --platform instagram --url "<instagram-reel-url>" --language en --prefer-subs --keep-temp
```

To write a markdown note:

```bash
python3 <georgeskills-root>/scripts/social_transcribe.py --platform instagram --url "<instagram-reel-url>" --prefer-subs --write-markdown --output-dir "<notes-dir>"
```

## Output Contract

Return:
- transcript
- whether it came from native captions/subtitles or Whisper fallback
- any major caveats such as partial text, music-heavy audio, multiple speakers, or low confidence segments

## Notes

- Instagram pages can be rate-limited or require rendering; prefer lightweight extraction first.
- If the video is inaccessible, private, region-blocked, or removed, say so directly.
- If the user needs bulk Instagram transcription, suggest building a helper script after confirming the exact input format.
