---
name: tiktok-transcribe-ops
description: Transcribe a TikTok video to text, preferring captions or subtitles before local audio fallback.
memory_tags:
  - domain:social-media
  - workflow:transcription
  - skill_role:researcher
  - repo_boundary:tools
  - inputs:web
  - outputs:transcript
  - risk:medium
---

# TikTok Transcribe Ops

Use when the user wants a transcript of a TikTok video.

## Goal

Produce a reliable transcript of a TikTok from the URL with a CLI-first workflow. Do not use browser automation by default, but allow screen-control fallback when the user asks for it or CLI extraction is blocked.

## Workflow

1. Confirm the target is a TikTok video URL.
2. Run the shared social transcription helper.
3. Prefer subtitle extraction when available.
4. Fall back to local audio transcription when subtitles are unavailable.
5. If CLI extraction cannot access the video and browser fallback is allowed, use the browser fallback rules below.
6. Return the transcript with a short provenance and confidence note.

## Preferred Order

1. Embedded or platform-provided captions and subtitle tracks fetched by CLI.
2. Local audio extraction plus Whisper transcription fallback.
3. Browser-assisted capture only when CLI paths fail or the user explicitly asks to use their browser session.

## Inputs

- TikTok video URL
- Optional output preference:
  - plain transcript
  - timestamps
  - transcript plus concise summary

## Extraction Rules

- Distinguish between creator caption text, hashtags, and spoken-word transcript.
- Prefer spoken-word transcript over decorative or promotional on-screen text.
- If the spoken words and on-screen captions diverge, prioritize the spoken audio and mention the mismatch.
- Mark transcripts as partial when only platform text is available and it does not cover the full audio.

## Audio Fallback

If caption extraction is not sufficient:

1. Acquire the audio or video with `yt-dlp`.
2. Extract audio to a temporary file.
3. Run the local Whisper transcription workflow.
4. Lightly clean the output while preserving meaning and speaker changes when obvious.

## Browser Fallback

If CLI/subtitle/audio acquisition is blocked:

Follow `skills/_shared/social-platform-fallbacks.md`. Capture only what is
needed for transcription: visible captions, creator text, page state, or a
locally acquired media/audio artifact.

## Local Helper

Primary entrypoint:

```bash
python3 <georgeskills-root>/scripts/social_transcribe.py --platform tiktok --url "<tiktok-url>"
```

Optional flags:

```bash
python3 <georgeskills-root>/scripts/social_transcribe.py --platform tiktok --url "<tiktok-url>" --language en --prefer-subs --keep-temp
```

To write a markdown note:

```bash
python3 <georgeskills-root>/scripts/social_transcribe.py --platform tiktok --url "<tiktok-url>" --prefer-subs --write-markdown --output-dir "<notes-dir>"
```

## Output Contract

Return:
- transcript
- source path used: platform captions/subtitles or Whisper fallback
- caveats such as partial coverage, background music, clipped speech, multiple speakers, or low confidence sections

## Notes

- TikTok often exposes short text that is not a complete transcript; do not overstate completeness.
- If the page is blocked, private, removed, or region-restricted, report that clearly.
- For repeated TikTok transcript work, suggest a dedicated helper script once the user’s exact workflow is clear.
