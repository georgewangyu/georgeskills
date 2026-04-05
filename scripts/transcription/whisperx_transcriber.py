import os
import argparse
import logging
import gc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Patch for PyTorch 2.6+ security changes
# MUST be set before any torch imports
os.environ["TORCH_LOAD_WEIGHTS_ONLY"] = "0"

def get_best_device():
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    return "cpu"

def transcribe_and_diarize(audio_file, hf_token=None, device=None, compute_type=None, output_dir=None, prompt=None):
    if device is None:
        device = get_best_device()

    if compute_type is None:
        # MPS usually works best with float32 or float16 (depending on the model/layer)
        # int8 is mostly for CPU.
        compute_type = "float32" if device == "mps" else "int8"

    try:
        import whisperx
        from whisperx.diarize import DiarizationPipeline
    except ImportError:
        logging.error("whisperx is not installed. Please run `pip install whisperx`")
        return None

    logging.info(f"Loading whisperx on {device} (Mode: {compute_type})...")

    # 1. Transcribe with Whisper (Large-v3)
    logging.info("Loading base transcription model...")
    model = whisperx.load_model("large-v3", device, compute_type=compute_type)

    logging.info(f"Loading audio file: {audio_file}...")
    audio = whisperx.load_audio(audio_file)

    logging.info("Step 1: Transcribing audio (Whisper Pass)...")
    # We use auto-detection by not passing a hardcoded language
    # Standard whisperx.transcribe doesn't always support initial_prompt,
    # so we keep it clean for maximum stability across versions.
    result = model.transcribe(audio, batch_size=16)
    logging.info(f"Detected language: {result['language']}")

    # 2. Speaker Diarization
    if not hf_token:
        logging.warning("No HuggingFace token provided. Skipping automatic speaker labeling.")
    else:
        try:
            logging.info(f"Step 2: Running pyannote speaker diarization on {device}...")
            diarize_model = DiarizationPipeline(use_auth_token=hf_token, device=device)
            diarize_segments = diarize_model(audio)

            logging.info("Step 3: Assigning speakers to segments...")
            result = whisperx.assign_word_speakers(diarize_segments, result)
        except Exception as e:
            logging.error(f"Diarization pass failed: {e}. Outputting unlabeled transcript instead.")

    # 3. Formatting output
    logging.info("Formatting transcript...")
    formatted_transcript = []

    current_speaker = None
    current_text = ""

    for segment in result["segments"]:
        speaker = segment.get("speaker", "SPEAKER_UNKNOWN")
        text = segment["text"].strip()

        if speaker == current_speaker:
            current_text += " " + text
        else:
            if current_speaker is not None:
                formatted_transcript.append(f"**{current_speaker}**: {current_text}")
            current_speaker = speaker
            current_text = text

    if current_speaker is not None:
        formatted_transcript.append(f"**{current_speaker}**: {current_text}")

    final_text = "\n\n".join(formatted_transcript)

    if output_dir:
        base_name = os.path.basename(audio_file).split('.')[0]
        out_path = os.path.join(output_dir, f"{base_name}_transcript.md")
        with open(out_path, "w") as f:
            f.write(f"# Transcript for {base_name}\n\n")
            f.write(final_text)
        logging.info(f"Final labeled transcript written to {out_path}")
    else:
        print("\n--- TRANSCRIPT ---\n")
        print(final_text)
        print("\n------------------\n")

    return final_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe an audio file with Speaker Diarization.")
    parser.add_argument("audio_file", help="Path to the audio file (.wav, .mp3, etc.)")
    parser.add_argument("--hf-token", default=os.environ.get("HF_TOKEN"), help="HuggingFace API token for Diarization")
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"], help="Device to run on (cpu, cuda, mps)")
    parser.add_argument("--outdir", help="Directory to save the markdown transcript.")
    parser.add_argument("--compute-type", choices=["int8", "float16", "float32"], help="Compute type (int8 for CPU, float16/32 for GPU)")
    parser.add_argument("--prompt", help="Optional initial prompt for Whisper (e.g. to force Simplified Chinese).")

    args = parser.parse_args()

    if not os.path.exists(args.audio_file):
        logging.error(f"File not found: {args.audio_file}")
        exit(1)

    transcribe_and_diarize(args.audio_file, hf_token=args.hf_token, device=args.device, output_dir=args.outdir, compute_type=args.compute_type, prompt=args.prompt)
