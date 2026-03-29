#!/usr/bin/env python3
"""Transcribe a YouTube video to plain text.

Preferred path:
1. Fetch creator subtitles or YouTube auto-captions via yt-dlp.
2. Convert VTT captions to plain text.

Fallback path:
3. Download audio via yt-dlp.
4. Run the local whisper CLI to generate a text transcript.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from html import unescape
from pathlib import Path


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise RuntimeError(f"Command failed: {' '.join(args)}\n{detail}")
    return result


def require_command(name: str) -> None:
    if shutil.which(name):
        return
    raise RuntimeError(f"Required command not found on PATH: {name}")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_value).strip("-._")
    return cleaned or "youtube-transcript"


def get_video_metadata(url: str) -> dict:
    result = run_command(
        ["uvx", "--from", "yt-dlp", "yt-dlp", "--dump-single-json", "--no-playlist", url]
    )
    return json.loads(result.stdout)


def build_subtitle_languages(language: str | None, explicit: str | None) -> str:
    if explicit:
        return explicit
    if not language:
        return "all,-live_chat"
    return ",".join([language, f"{language}-orig", f"{language}-{language}"])


def write_subtitles(url: str, temp_dir: Path, languages: str) -> list[Path]:
    output_template = str(temp_dir / "%(id)s.%(ext)s")
    result = run_command(
        [
            "uvx",
            "--from",
            "yt-dlp",
            "yt-dlp",
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-format",
            "vtt",
            "--sub-langs",
            languages,
            "-o",
            output_template,
            url,
        ],
        check=False,
    )
    subtitle_files = sorted(temp_dir.glob("*.vtt"))
    if subtitle_files:
        return subtitle_files
    if result.returncode != 0:
        return []
    return subtitle_files


def choose_best_subtitle(subtitle_files: list[Path], language: str | None) -> Path:
    language = language or "en"
    preference = [
        f".{language}-orig.vtt",
        f".{language}.vtt",
        f".{language}-{language}.vtt",
    ]

    def rank(path: Path) -> tuple[int, int]:
        for index, suffix in enumerate(preference):
            if path.name.endswith(suffix):
                return (index, -len(path.name))
        return (len(preference), -len(path.name))

    return sorted(subtitle_files, key=rank)[0]


def clean_vtt_text(raw_text: str) -> str:
    lines: list[str] = []
    previous = ""
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "WEBVTT" or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if line.startswith("NOTE"):
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = unescape(line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if line == previous:
            continue
        lines.append(line)
        previous = line
    return "\n".join(lines).strip() + "\n"


def find_downloaded_audio(temp_dir: Path) -> Path:
    candidates = sorted(
        path for path in temp_dir.iterdir() if path.is_file() and path.suffix.lower() not in {".vtt", ".txt", ".json"}
    )
    if not candidates:
        raise RuntimeError("yt-dlp did not produce an audio file.")
    return candidates[0]


def transcribe_audio_with_whisper(
    audio_path: Path, temp_dir: Path, model: str, language: str | None
) -> Path:
    require_command("whisper")
    command = [
        "whisper",
        str(audio_path),
        "--task",
        "transcribe",
        "--model",
        model,
        "--output_format",
        "txt",
        "--output_dir",
        str(temp_dir),
        "--verbose",
        "False",
    ]
    if language:
        command.extend(["--language", language])
    run_command(command)
    transcript_path = temp_dir / f"{audio_path.stem}.txt"
    if not transcript_path.exists():
        raise RuntimeError("Whisper completed but no transcript file was created.")
    return transcript_path


def download_audio(url: str, temp_dir: Path) -> Path:
    require_command("ffmpeg")
    output_template = str(temp_dir / "%(id)s.%(ext)s")
    run_command(
        [
            "uvx",
            "--from",
            "yt-dlp",
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "-o",
            output_template,
            url,
        ]
    )
    return find_downloaded_audio(temp_dir)


def build_output_path(output_arg: str | None, output_dir_arg: str | None, stem: str) -> Path:
    if output_arg:
        output_path = Path(output_arg).expanduser()
        return output_path if output_path.suffix else output_path.with_suffix(".txt")
    if output_dir_arg:
        return Path(output_dir_arg).expanduser() / f"{stem}.txt"
    return Path.cwd() / "transcripts" / f"{stem}.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe a YouTube video to text.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--output", help="Output file path for the transcript")
    parser.add_argument("--output-dir", help="Directory to write the transcript into")
    parser.add_argument(
        "--language",
        default="en",
        help="Preferred transcript language for subtitles/Whisper. Use 'auto' for Whisper autodetect.",
    )
    parser.add_argument(
        "--subtitle-languages",
        help="yt-dlp subtitle language selector, used before Whisper fallback",
    )
    parser.add_argument(
        "--model",
        default="turbo",
        help="Whisper model to use when subtitles are unavailable",
    )
    args = parser.parse_args()

    language = None if args.language == "auto" else args.language
    subtitle_languages = build_subtitle_languages(language, args.subtitle_languages)

    metadata = get_video_metadata(args.url)
    title = metadata.get("title") or metadata.get("id") or "youtube-video"
    video_id = metadata.get("id", "video")
    output_stem = slugify(f"{title}-{video_id}")
    output_path = build_output_path(args.output, args.output_dir, output_stem)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="youtube-transcribe-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        subtitle_files = write_subtitles(args.url, temp_dir, subtitle_languages)
        if subtitle_files:
            subtitle_path = choose_best_subtitle(subtitle_files, language)
            transcript_text = clean_vtt_text(subtitle_path.read_text(encoding="utf-8"))
            if not transcript_text.strip():
                raise RuntimeError("Subtitle file was downloaded but no transcript text could be extracted.")
            output_path.write_text(transcript_text, encoding="utf-8")
            source = f"subtitles:{subtitle_path.name}"
        else:
            audio_path = download_audio(args.url, temp_dir)
            transcript_path = transcribe_audio_with_whisper(audio_path, temp_dir, args.model, language)
            shutil.copyfile(transcript_path, output_path)
            source = f"whisper:{args.model}"

    print(json.dumps({"output_path": str(output_path), "title": title, "video_id": video_id, "source": source}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
