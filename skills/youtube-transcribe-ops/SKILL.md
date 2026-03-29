---
name: youtube-transcribe-ops
description: Transcribe a YouTube video to text when the user provides a YouTube link or asks for a transcript. Prefer existing subtitles or auto-captions first, then fall back to local Whisper transcription when captions are unavailable.
memory_tags:
  - domain:media
  - workflow:transcription
  - repo_boundary:tools
  - data_class:public-derived
  - risk:medium
---

# YouTube Transcribe Ops

## Trigger

Use when:
- the user gives a YouTube URL and wants the video transcribed
- the user asks for a transcript, captions dump, or text extraction from a YouTube video

Do not use when:
- the source is not YouTube
- the user wants a summary only and does not need the transcript itself

## Inputs

- Required: one YouTube URL
- Optional: output path, preferred language, Whisper model

## Workflow

1. Run `skills/youtube-transcribe-ops/scripts/transcribe_youtube.py <youtube-url>`.
2. Let the script try subtitles or auto-captions first.
3. If captions are missing, let the script download audio and transcribe with the local `whisper` CLI.
4. Return the saved transcript path to the user and provide the transcript inline when useful.

## Notes

- The script uses `uvx --from yt-dlp yt-dlp`, so `yt-dlp` does not need to be preinstalled.
- `ffmpeg` and `whisper` must be available for the audio-transcription fallback path.
- Default output goes to `./transcripts/`.
