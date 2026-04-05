---
name: transcribe-offline-meeting
description: Processes offline audio recordings from an external mic into the daily log pipeline.
version: 1.0
tags:
  - audio
  - journal
  - transcription
---
# Transcribe Offline Meeting

## Purpose
This skill defines the process for an agent to take a raw `.wav` or `.mp3` file (typically recorded offline via a DJI Mic 2 or Dictaphone), transcribe it using Whisper (Transcription Only), and then use the AI's natural language understanding to provide a speaker-labeled summary in the LifeRepo `DAILY_SUMMARY_WORKFLOW`.

## Script Usage
The core transcription utility is located at:
`georgeskills/scripts/transcription/whisperx_transcriber.py`

### PREREQUISITES
1. The agent/user must use the native ARM64 virtual environment:
   `source georgeskills/scripts/transcription/venv/bin/activate`

## Execution

You have two modes depending on your recording length and hardware:

### Option A: Balanced Mode (WhisperX)
*Best for short files (< 15 mins) where you want a backup speaker-label pass.*
```bash
source georgeskills/scripts/transcription/venv/bin/activate
source georgerepo/.tokens/huggingface.env
python georgeskills/scripts/transcription/whisperx_transcriber.py /path/to/file.wav --device cpu --outdir /georgerepo/journal/inbox/
```

### Option B: Hyper-Speed Mode (MLX)
*Best for long files (hours long). Uses Mac GPU/Neural Engine. 5x-10x faster.*
```bash
source georgeskills/scripts/transcription/venv/bin/activate
python georgeskills/scripts/transcription/mlx_transcriber.py /path/to/file.wav --outdir /georgerepo/journal/inbox/
```

## AI Processing & Export

After the script generates the raw transcript:

1. **Read** the generated markdown transcript file.
2. **Label Speakers:** Since machine diarization is often skipped in fast mode, the agent MUST manually identify the speakers (e.g., "George", "Teresa") based on the context.
3. **Rewrite & Synthesize:**
   - Rewrite the raw transcript into a clean dialogue format if requested.
   - Summarize high-level topics, constraints, and decisions.
4. **Format:** Output the synthesis under the `## Conversation Milestones` header using the personality guidelines in `georgerepo/journal/PRIVATE-journal.md`.
5. **Append:** Merge this new block directly into today's `Summary.md`.
