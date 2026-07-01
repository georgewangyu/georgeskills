---
name: youtube-transcribe-ops
description: Transcribe a YouTube video to text, preferring subtitles or auto-captions before local Whisper fallback.
memory_tags:
  - domain:media
  - workflow:transcription
  - skill_role:researcher
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
4. For GeorgeRepo/private-workspace runs, do not leave final artifacts in the workspace root `./transcripts/` folder:
   - raw subtitle/audio-derived files go under `georgerepo/areas/transcripts/raw/youtube/<video-id>/`
   - readable transcript Markdown goes under `georgerepo/areas/transcripts/processed/youtube/`
5. Convert cleaned transcript text to readable Markdown with `docconvert/skills/doc-convert/scripts/convert_to_markdown.py` when that repo is available, then wrap the result with GeorgeRepo frontmatter, source metadata, raw artifact links, and timestamp headings.
6. Return the saved Markdown transcript path to the user. Return raw artifact paths only as supporting provenance.

## Notes

- The script uses `uvx --from yt-dlp yt-dlp`, so `yt-dlp` does not need to be preinstalled.
- `ffmpeg` and `whisper` must be available for the audio-transcription fallback path.
- Avoid workspace-root `./transcripts/` except as a temporary scratch location. The durable private default is GeorgeRepo: raw source in `areas/transcripts/raw/`, human-readable Markdown in `areas/transcripts/processed/`.
