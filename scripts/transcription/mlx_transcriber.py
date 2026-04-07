import os
import argparse
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def transcribe_mlx(audio_file, model_name="mlx-community/whisper-large-v3-mlx-4bit", output_dir=None):
    try:
        import mlx_whisper
    except ImportError:
        logging.error("mlx-whisper is not installed. Please run `pip install mlx-whisper` in your venv.")
        return None

    logging.info(f"Loading MLX Hyper-Speed Transcriber (Model: {model_name})...")

    start_time = time.time()

    try:
        logging.info(f"Transcribing audio file: {audio_file}...")
        # MLX-Whisper automatically loads the model from HuggingFace cache and runs on GPU
        result = mlx_whisper.transcribe(audio_file, path_or_hf_repo=model_name)
    except Exception as e:
        logging.error(f"MLX Transcription failed: {e}")
        return None

    duration = time.time() - start_time
    logging.info(f"Transcription complete in {duration:.2f} seconds.")

    # Formatting output (Segmented with timestamps)
    logging.info("Formatting transcript...")
    formatted_transcript = []

    # MLX result structure matches OpenAI Whisper
    for segment in result["segments"]:
        text = segment["text"].strip()
        start = segment["start"]
        end = segment["end"]
        # Standard timestamp format for AI parsing
        formatted_transcript.append(f"[{start:.2f}s - {end:.2f}s] {text}")

    final_text = "\n\n".join(formatted_transcript)

    if output_dir:
        base_name = os.path.basename(audio_file).rsplit('.', 1)[0]
        out_path = os.path.join(output_dir, f"{base_name}_transcript.md")
        os.makedirs(output_dir, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(f"# MLX High-Speed Transcript for {base_name}\n\n")
            f.write(f"> [!NOTE]\n> **Mode:** Super-Speed (MLX 4-bit)\n> **Processing Time:** {duration:.2f}s\n\n")
            f.write(final_text)
        logging.info(f"Transcript written to {out_path}")
    else:
        print("\n--- MLX TRANSCRIPT ---\n")
        print(final_text)
        print("\n----------------------\n")

    return final_text

def resolve_output_dir(audio_file, base_outdir):
    """
    If the audio filename contains a date in the DJI format (DJI_XX_YYYYMMDD_HHMMSS),
    automatically resolve the output dir to base_outdir/YYYY/MM/.
    Falls back to base_outdir unchanged if no date can be parsed.
    """
    import re
    basename = os.path.basename(audio_file)
    match = re.search(r'_(\d{4})(\d{2})\d{2}_', basename)
    if match:
        year, month = match.group(1), match.group(2)
        return os.path.join(base_outdir, year, month)
    return base_outdir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe an audio file using MLX (Super-Speed for Apple Silicon).")
    parser.add_argument("audio_file", help="Path to the audio file (.wav, .mp3, etc.)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-mlx-4bit", help="MLX-compatible model repo on HuggingFace.")
    parser.add_argument("--outdir", help="Base directory to save the markdown transcript. Date-based YYYY/MM subdir is created automatically from the filename.")

    args = parser.parse_args()

    if not os.path.exists(args.audio_file):
        logging.error(f"File not found: {args.audio_file}")
        exit(1)

    output_dir = resolve_output_dir(args.audio_file, args.outdir) if args.outdir else None
    transcribe_mlx(args.audio_file, model_name=args.model, output_dir=output_dir)
