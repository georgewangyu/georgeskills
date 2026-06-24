---
name: transcribe-offline-meeting
description: Processes offline audio recordings from an external mic into the daily log pipeline.
metadata:
  version: 1.0
  tags:
    - audio
    - journal
    - transcription
---
# Transcribe Offline Meeting

## Purpose
This skill defines the process for an agent to take a raw `.wav` or `.mp3` file
(typically recorded offline via a DJI Mic 2 or Dictaphone), transcribe it using
the native ARM64 MLX Whisper path, and then use the AI's natural language
understanding to provide a speaker-labeled summary in the LifeRepo
`DAILY_SUMMARY_WORKFLOW`.

## Script Usage
The core transcription utility is located at:
`georgeskills/scripts/transcription/mlx_transcriber.py`

### PREREQUISITES
1. The agent/user must use the native ARM64 virtual environment:
   `source georgeskills/scripts/transcription/venv/bin/activate`

## Execution

Use the MLX path for transcription. Do not choose WhisperX,
`whisper-ctranslate2`, or generic CPU Whisper as a normal fallback for this
workflow. If MLX fails, fix the MLX environment first: native ARM64 venv,
working `mlx` / `mlx_whisper` imports, and a valid Hugging Face cache.

```bash
source georgeskills/scripts/transcription/venv/bin/activate
HF_HOME=<stable-huggingface-cache> python georgeskills/scripts/transcription/mlx_transcriber.py /path/to/file.wav --outdir /georgerepo/journal/audio/transcripts/
```

Current defaults for the MLX path:
- model: `mlx-community/whisper-large-v3-turbo`
- preprocessing: built-in silence trimming / energy-based VAD before transcription
- fallback: if the turbo model fails to load or run, the script retries `mlx-community/whisper-large-v3-mlx-4bit`
- environment: use the native ARM64 transcription venv. If the default
  Hugging Face cache is stale or points at a missing volume, set `HF_HOME` to a
  stable local cache before running the MLX script.

Do not use the old CPU transcriber to work around a local setup issue. Treat
MLX import/cache/model failures as environment blockers and record the blocker
in the daily summary or command notes.

Storage rule:
- Keep `Workspace/dji-audio/` raw-only.
- Put generated transcripts under `<private-repo>/journal/audio/transcripts/YYYY/MM/`.
- The MLX transcriber now defaults to `<private-repo>/journal/audio/transcripts/` and auto-redirects the legacy `dji-audio/transcripts/` and `journal/inbox/` targets back into the canonical journal audio tree.

## AI Processing & Export

After the script generates the raw transcript:

1. **Read** the generated markdown transcript file.
2. **Label Speakers:** Since machine diarization is often skipped in fast mode, the agent MUST manually identify the speakers (e.g., "George", "Teresa") based on the context.
3. **Rewrite & Synthesize:**
   - Rewrite the raw transcript into a clean dialogue format if requested.
   - Summarize high-level topics, constraints, and decisions.
4. **Format:** Output the synthesis under the `## Conversation Milestones` header using the personality guidelines in `georgerepo/journal/PRIVATE-journal.md`.
5. **Append:** Merge this new block directly into today's `Summary.md`.
