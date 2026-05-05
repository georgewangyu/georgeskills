---
name: durable-transcript-archive-ops
description: Preserve transcripts and source media into a durable archive after transcription, including raw artifact placement, processed Markdown, provenance metadata, duplicate-layout cleanup, and journal or research handoff notes.
memory_tags:
  - domain:media
  - workflow:transcript-archiving
  - repo_boundary:tools
  - inputs:media-artifacts
  - outputs:archived-transcript
  - risk:medium
---

# Durable Transcript Archive Ops

## Trigger

Use when:
- a transcript was generated and needs to be saved durably
- raw media, captions, Whisper output, and processed Markdown need consistent placement
- transcription fallback paths created scattered files that should be normalized
- the user wants provenance preserved for later search, research, or journal context

Do not use when:
- the user only wants a quick summary and no durable artifact
- the source-specific transcription skill has not yet produced any transcript or media artifact
- the task is OCR or PDF reconstruction rather than audio/video transcript archiving

## Inputs

- Required: source URL or local media path, transcript text or transcript artifact path, desired archive namespace
- Optional: title, source platform, creator/channel, publication date, raw artifacts, summary, related journal date

## Workflow

1. Identify source and archive namespace:
   - platform or source type
   - stable source ID when available
   - target archive root supplied by the user or private repo convention
2. Preserve raw artifacts:
   - original media when downloaded
   - subtitle/caption files
   - raw Whisper or ASR output
   - command notes when a fallback path was needed
3. Create processed Markdown:
   - title and source metadata
   - transcript body
   - timestamp headings when available
   - links or relative references to raw artifacts
   - provenance note describing caption vs ASR vs manual cleanup
4. Normalize layout:
   - avoid duplicate root folders
   - move scratch outputs into the archive tree
   - do not delete raw files unless the user explicitly asks
5. Add a concise handoff note:
   - transcript saved path
   - raw artifact path
   - fallback used
   - whether the transcript is ready for summarization, research, or journal ingestion

## Output Contract

Return:
- processed Markdown transcript path
- raw artifact paths
- provenance/fallback note
- cleanup performed or still needed
- suggested next step: summarize, extract ideas, cite in journal, or leave archived

## Boundaries

- This skill archives artifacts; use source-specific skills for extraction first.
- Do not invent metadata that cannot be inferred from source or user input.
- Do not copy private media into public repos.
- Keep path examples generic and prefer `<private-repo>` placeholders.
