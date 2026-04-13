import os
import sys
import argparse
import logging
import tempfile
import time
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
JOURNAL_OPS_SCRIPTS = WORKSPACE_ROOT / "georgeskills" / "skills" / "journal-ops" / "scripts"
if JOURNAL_OPS_SCRIPTS.exists():
    sys.path.insert(0, str(JOURNAL_OPS_SCRIPTS))

try:
    from repo_paths import resolve_private_repo_root
except Exception:
    resolve_private_repo_root = None

DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
FALLBACK_MODEL = "mlx-community/whisper-large-v3-mlx-4bit"


def transcribe_mlx(audio_file, model_name=DEFAULT_MODEL, output_dir=None, use_vad=True):
    try:
        import mlx_whisper
    except ImportError:
        logging.error("mlx-whisper is not installed. Please run `pip install mlx-whisper` in your venv.")
        return None

    logging.info(f"Loading MLX Hyper-Speed Transcriber (Model: {model_name})...")

    start_time = time.time()
    processing_note = "Speech-only fast path disabled"
    audio_for_transcription = audio_file
    vad_stats = None
    time_map = None

    with tempfile.TemporaryDirectory(prefix="mlx-transcriber-") as temp_dir:
        if use_vad:
            try:
                prepared_audio = Path(temp_dir) / "prepared.wav"
                trimmed_audio = Path(temp_dir) / "speech_only.wav"
                audio_for_transcription, time_map, vad_stats = build_vad_trimmed_audio(
                    audio_file,
                    prepared_audio,
                    trimmed_audio,
                )
                processing_note = (
                    "Energy-based VAD trim via ffmpeg+scipy "
                    f"({vad_stats['speech_ratio']:.1%} of source audio kept)"
                )
            except Exception as exc:
                logging.warning("VAD preprocessing failed, falling back to raw audio: %s", exc)

        result = None
        attempted_models = [model_name]
        if model_name == DEFAULT_MODEL:
            attempted_models.append(FALLBACK_MODEL)

        for candidate_model in attempted_models:
            try:
                logging.info("Transcribing audio file: %s", audio_for_transcription)
                logging.info("Using MLX model: %s", candidate_model)
                # MLX-Whisper automatically loads the model from HuggingFace cache and runs on GPU
                result = mlx_whisper.transcribe(audio_for_transcription, path_or_hf_repo=candidate_model)
                model_name = candidate_model
                break
            except Exception as exc:
                logging.warning("MLX transcription failed with %s: %s", candidate_model, exc)

        if result is None:
            logging.error("MLX transcription failed for all attempted models.")
            return None

    duration = time.time() - start_time
    logging.info(f"Transcription complete in {duration:.2f} seconds.")

    # Formatting output (Segmented with timestamps)
    logging.info("Formatting transcript...")
    formatted_transcript = []

    # MLX result structure matches OpenAI Whisper
    for segment in result["segments"]:
        text = segment["text"].strip()
        start = remap_trimmed_time(segment["start"], time_map)
        end = remap_trimmed_time(segment["end"], time_map, prefer_end=True)
        # Standard timestamp format for AI parsing
        formatted_transcript.append(f"[{start:.2f}s - {end:.2f}s] {text}")

    final_text = "\n\n".join(formatted_transcript)

    if output_dir:
        base_name = os.path.basename(audio_file).rsplit('.', 1)[0]
        out_path = os.path.join(output_dir, f"{base_name}_transcript.md")
        os.makedirs(output_dir, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(f"# MLX High-Speed Transcript for {base_name}\n\n")
            f.write(
                f"> [!NOTE]\n"
                f"> **Mode:** Super-Speed ({model_name})\n"
                f"> **Processing Time:** {duration:.2f}s\n"
                f"> **Preprocessing:** {processing_note}\n"
            )
            if vad_stats:
                f.write(
                    f"> **VAD Stats:** kept {vad_stats['kept_seconds']:.2f}s / "
                    f"{vad_stats['source_seconds']:.2f}s across {vad_stats['interval_count']} speech segments\n"
                )
            f.write("\n")
            f.write(final_text)
        logging.info(f"Transcript written to {out_path}")
    else:
        print("\n--- MLX TRANSCRIPT ---\n")
        print(final_text)
        print("\n----------------------\n")

    return final_text


def run_ffmpeg_to_wav(audio_file, output_wav):
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        audio_file,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(output_wav),
    ]
    subprocess.run(command, check=True)


def detect_speech_intervals(samples, sample_rate, frame_ms=30, min_speech_ms=240, max_silence_ms=700, pad_ms=180):
    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    samples = samples.astype(np.float32)
    peak = np.max(np.abs(samples)) or 1.0
    samples = samples / peak

    frame_samples = max(1, int(sample_rate * frame_ms / 1000))
    min_speech_frames = max(1, int(min_speech_ms / frame_ms))
    max_silence_frames = max(1, int(max_silence_ms / frame_ms))
    pad_samples = int(sample_rate * pad_ms / 1000)

    frame_energies = []
    for index in range(0, len(samples), frame_samples):
        frame = samples[index:index + frame_samples]
        if len(frame) == 0:
            continue
        rms = np.sqrt(np.mean(np.square(frame)) + 1e-12)
        frame_energies.append(20 * np.log10(rms + 1e-12))

    if not frame_energies:
        return [(0, len(samples))]

    energies = np.array(frame_energies, dtype=np.float32)
    noise_floor = float(np.percentile(energies, 20))
    speech_peak = float(np.percentile(energies, 95))
    threshold = min(max(noise_floor + 8.0, -42.0), speech_peak - 2.0)

    speech_mask = energies >= threshold
    intervals = []
    current_start = None
    trailing_silence = 0

    for frame_index, is_speech in enumerate(speech_mask):
        if is_speech:
            if current_start is None:
                current_start = frame_index
            trailing_silence = 0
            continue
        if current_start is None:
            continue
        trailing_silence += 1
        if trailing_silence >= max_silence_frames:
            speech_end = frame_index - trailing_silence + 1
            if speech_end - current_start >= min_speech_frames:
                intervals.append((current_start, speech_end))
            current_start = None
            trailing_silence = 0

    if current_start is not None:
        speech_end = len(speech_mask)
        if speech_end - current_start >= min_speech_frames:
            intervals.append((current_start, speech_end))

    if not intervals:
        return [(0, len(samples))]

    merged_intervals = []
    for frame_start, frame_end in intervals:
        sample_start = max(0, frame_start * frame_samples - pad_samples)
        sample_end = min(len(samples), frame_end * frame_samples + pad_samples)
        if merged_intervals and sample_start <= merged_intervals[-1][1]:
            merged_intervals[-1] = (merged_intervals[-1][0], max(merged_intervals[-1][1], sample_end))
        else:
            merged_intervals.append((sample_start, sample_end))
    return merged_intervals


def write_trimmed_audio(samples, sample_rate, intervals, output_wav):
    chunks = []
    time_map = []
    trimmed_offset = 0.0

    for start_sample, end_sample in intervals:
        chunk = samples[start_sample:end_sample]
        if len(chunk) == 0:
            continue
        chunks.append(chunk)
        original_start = start_sample / sample_rate
        original_end = end_sample / sample_rate
        trimmed_start = trimmed_offset
        trimmed_end = trimmed_start + (len(chunk) / sample_rate)
        trimmed_offset = trimmed_end
        time_map.append(
            {
                "trimmed_start": trimmed_start,
                "trimmed_end": trimmed_end,
                "original_start": original_start,
                "original_end": original_end,
            }
        )

    if not chunks:
        wavfile.write(output_wav, sample_rate, samples)
        return str(output_wav), None

    concatenated = np.concatenate(chunks)
    wavfile.write(output_wav, sample_rate, concatenated)
    return str(output_wav), time_map


def build_vad_trimmed_audio(audio_file, prepared_wav, trimmed_wav):
    run_ffmpeg_to_wav(audio_file, prepared_wav)
    sample_rate, samples = wavfile.read(prepared_wav)
    intervals = detect_speech_intervals(samples, sample_rate)
    trimmed_audio, time_map = write_trimmed_audio(samples, sample_rate, intervals, trimmed_wav)

    source_seconds = len(samples) / sample_rate
    kept_seconds = sum((end - start) / sample_rate for start, end in intervals)
    vad_stats = {
        "source_seconds": source_seconds,
        "kept_seconds": kept_seconds,
        "speech_ratio": kept_seconds / source_seconds if source_seconds else 1.0,
        "interval_count": len(intervals),
    }
    return trimmed_audio, time_map, vad_stats


def remap_trimmed_time(timestamp, time_map, prefer_end=False):
    if not time_map:
        return timestamp

    for interval in time_map:
        if interval["trimmed_start"] <= timestamp <= interval["trimmed_end"]:
            return interval["original_start"] + (timestamp - interval["trimmed_start"])

    if timestamp < time_map[0]["trimmed_start"]:
        return time_map[0]["original_start"]

    boundary_key = "original_end" if prefer_end else "original_start"
    for interval in reversed(time_map):
        if timestamp >= interval["trimmed_end"]:
            return interval[boundary_key]

    return timestamp

def resolve_output_dir(audio_file, base_outdir):
    """
    If the audio filename contains a date in the DJI format (DJI_XX_YYYYMMDD_HHMMSS),
    automatically resolve the output dir to base_outdir/YYYY/MM/.
    Falls back to base_outdir unchanged if no date can be parsed.
    """
    import re
    if base_outdir is None:
        base_outdir = default_output_dir()
    else:
        base_outdir = normalize_output_dir(base_outdir)
    basename = os.path.basename(audio_file)
    match = re.search(r'_(\d{4})(\d{2})\d{2}_', basename)
    if match:
        year, month = match.group(1), match.group(2)
        return os.path.join(base_outdir, year, month)
    return base_outdir


def default_output_dir():
    if resolve_private_repo_root is not None:
        try:
            return str(resolve_private_repo_root() / "journal" / "audio" / "transcripts")
        except Exception:
            pass
    return None


def normalize_output_dir(base_outdir):
    raw_path = Path(base_outdir).expanduser()
    normalized = raw_path.resolve(strict=False)
    parts = normalized.parts
    if len(parts) >= 2 and parts[-2:] == ("dji-audio", "transcripts"):
        journal_dir = default_output_dir()
        if journal_dir is not None:
            logging.warning(
                "Redirecting legacy transcript destination %s to %s so dji-audio stays raw-only.",
                normalized,
                journal_dir,
            )
            return journal_dir
    if len(parts) >= 2 and parts[-2:] == ("journal", "inbox"):
        journal_dir = default_output_dir()
        if journal_dir is not None:
            logging.warning(
                "Redirecting legacy transcript destination %s to %s so journal audio transcripts stay in one canonical tree.",
                normalized,
                journal_dir,
            )
            return journal_dir
    return str(normalized)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe an audio file using MLX (Super-Speed for Apple Silicon).")
    parser.add_argument("audio_file", help="Path to the audio file (.wav, .mp3, etc.)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="MLX-compatible model repo on HuggingFace.")
    parser.add_argument("--no-vad", action="store_true", help="Disable the built-in silence trimming pass.")
    parser.add_argument(
        "--outdir",
        help=(
            "Base directory to save the markdown transcript. Defaults to "
            "<private-repo>/journal/audio/transcripts/. Date-based YYYY/MM subdir is created automatically from the filename."
        ),
    )

    args = parser.parse_args()

    if not os.path.exists(args.audio_file):
        logging.error(f"File not found: {args.audio_file}")
        exit(1)

    output_dir = resolve_output_dir(args.audio_file, args.outdir)
    transcribe_mlx(args.audio_file, model_name=args.model, output_dir=output_dir, use_vad=not args.no_vad)
