#!/usr/bin/env python3
"""Download subtitles or audio from short-form social video URLs and transcribe locally."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def find_tool(names: list[str]) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def read_subtitle_transcript(path: Path) -> str:
    text = read_text_file(path)
    lines = []
    seen_recent: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "WEBVTT":
            continue
        if "-->" in line:
            continue
        if line.isdigit():
            continue
        if re.fullmatch(r"[A-Za-z-]+:\s*.*", line) and line.split(":", 1)[0].lower() in {"kind", "language"}:
            continue
        if seen_recent and line == seen_recent[-1]:
            continue
        lines.append(line)
        seen_recent.append(line)
        if len(seen_recent) > 5:
            seen_recent.pop(0)
    if len(lines) % 2 == 0:
        midpoint = len(lines) // 2
        if lines[:midpoint] == lines[midpoint:]:
            lines = lines[:midpoint]
    return "\n".join(lines).strip()


def choose_transcriber() -> tuple[str, list[str]]:
    faster_whisper = find_tool(["faster-whisper"])
    if faster_whisper:
        return "faster-whisper", [faster_whisper]

    whisper = find_tool(["whisper"])
    if whisper:
        return "whisper", [whisper]

    uv = find_tool(["uv"])
    if uv:
        return "uvx-whisper", [uv, "tool", "run", "--from", "openai-whisper", "whisper"]

    return "", []


def choose_yt_dlp() -> tuple[str, list[str]]:
    yt_dlp = find_tool(["yt-dlp"])
    if yt_dlp:
        return "yt-dlp", [yt_dlp]

    uv = find_tool(["uv"])
    if uv:
        return "uvx-yt-dlp", [uv, "tool", "run", "--from", "yt-dlp", "yt-dlp"]

    return "", []


def fetch_metadata(yt_dlp_cmd: list[str], url: str) -> dict:
    cmd = yt_dlp_cmd + ["--dump-single-json", "--skip-download", url]
    completed = run(cmd)
    return json.loads(completed.stdout)


def fetch_subtitles(yt_dlp_cmd: list[str], url: str, outtmpl: str, language: str | None) -> Path | None:
    sub_lang = language or "en.*,orig,-live_chat"
    cmd = yt_dlp_cmd + [
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-format",
        "vtt/srt/best",
        "--sub-langs",
        sub_lang,
        "-o",
        outtmpl,
        url,
    ]
    run(cmd)
    candidates = sorted(Path(outtmpl).parent.glob("media*.vtt")) + sorted(Path(outtmpl).parent.glob("media*.srt"))
    return candidates[0] if candidates else None


def download_audio(yt_dlp_cmd: list[str], url: str, outtmpl: str) -> Path:
    cmd = yt_dlp_cmd + [
        "-f",
        "bestaudio/best",
        "-x",
        "--audio-format",
        "mp3",
        "-o",
        outtmpl,
        url,
    ]
    run(cmd)
    candidates = sorted(Path(outtmpl).parent.glob("media*.mp3")) + sorted(Path(outtmpl).parent.glob("media*.m4a"))
    if not candidates:
        raise FileNotFoundError("yt-dlp did not produce an audio file")
    return candidates[0]


def transcribe_audio(transcriber: str, base_cmd: list[str], audio_path: Path, language: str | None, output_dir: Path) -> Path:
    if transcriber == "faster-whisper":
        cmd = base_cmd + [str(audio_path), "--output_dir", str(output_dir)]
        if language:
            cmd += ["--language", language]
        run(cmd)
        txt_candidates = sorted(output_dir.glob(f"{audio_path.stem}*.txt"))
        if txt_candidates:
            return txt_candidates[0]
        raise FileNotFoundError("faster-whisper completed without producing a transcript")

    if transcriber == "whisper":
        cmd = base_cmd + [str(audio_path), "--output_format", "txt", "--output_dir", str(output_dir)]
        if language:
            cmd += ["--language", language]
        run(cmd)
        txt_candidates = sorted(output_dir.glob(f"{audio_path.stem}*.txt"))
        if txt_candidates:
            return txt_candidates[0]
        raise FileNotFoundError("whisper completed without producing a transcript")

    raise RuntimeError("no supported transcription CLI found")


def derive_source_id(url: str, metadata: dict) -> str:
    if metadata.get("id"):
        return str(metadata["id"])
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if path_parts:
        return path_parts[-1]
    return "unknown"


def write_markdown_note(output_dir: Path, payload: dict, metadata: dict) -> Path:
    title = metadata.get("title") or f"{payload['platform'].title()} Transcript"
    uploader = metadata.get("uploader") or metadata.get("channel") or "unknown"
    source_id = derive_source_id(payload["url"], metadata)
    upload_date = metadata.get("upload_date")
    if upload_date and len(str(upload_date)) == 8:
        source_date = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    else:
        source_date = dt.date.today().isoformat()
    filename = f"{source_date}_{payload['platform']}_{slugify(title)[:80]}.md"
    doc_id = f"georgerepo/social-media/video/transcripts/{payload['platform']}/{source_date}_{slugify(title)[:80]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    note_path = output_dir / filename

    lines = [
        "---",
        'doc_schema: "doc-frontmatter-v1"',
        f'doc_id: "{doc_id}"',
        'doc_type: "social-media_doc"',
        'doc_status: "active"',
        f'title: "{title.replace(chr(34), chr(39))} — Transcript"',
        f'description: "Transcript capture for {payload["platform"]} source {source_id}."',
        "memory_eligible: true",
        'memory_priority: "medium"',
        "doc_tags:",
        '  - "domain:social-media"',
        '  - "visibility:private"',
        '  - "type:social-media_doc"',
        f'  - "platform:{payload["platform"]}"',
        '  - "artifact:transcript"',
        "---",
        f"# {title} — Transcript",
        "",
        "## Source",
        f"- Platform: `{payload['platform']}`",
        f"- URL: {payload['url']}",
        f"- Creator: `{uploader}`",
        f"- Source ID: `{source_id}`",
        f"- Extraction Method: `{payload['method']}`",
    ]
    if metadata.get("duration_string"):
        lines.append(f"- Duration: `{metadata['duration_string']}`")
    elif metadata.get("duration"):
        lines.append(f"- Duration: `{int(metadata['duration'])}s`")

    lines += [
        "",
        "## Notes",
        f"- Captured: `{dt.datetime.now().astimezone().isoformat(timespec='seconds')}`",
        "- Transcript may include platform subtitle artifacts or ASR mistakes.",
        "",
        "## Transcript",
        "",
        "```text",
        payload["transcript"],
        "```",
        "",
    ]
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return note_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["tiktok", "instagram"], required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--language")
    parser.add_argument("--prefer-subs", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--write-markdown", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    yt_dlp_name, yt_dlp_cmd = choose_yt_dlp()
    if not yt_dlp_cmd:
        print(json.dumps({"ok": False, "error": "Missing downloader: yt-dlp or uv"}))
        return 1

    transcriber, transcriber_cmd = choose_transcriber()
    if not transcriber:
        print(json.dumps({"ok": False, "error": "Missing supported transcription CLI: faster-whisper or whisper"}))
        return 1

    workdir_cm = tempfile.TemporaryDirectory(prefix=f"{args.platform}_transcribe_")
    workdir = Path(workdir_cm.name)
    outtmpl = str(workdir / "media.%(ext)s")

    try:
        try:
            metadata = fetch_metadata(yt_dlp_cmd, args.url)
        except subprocess.CalledProcessError:
            metadata = {}
        subtitle_path = None
        if args.prefer_subs:
            try:
                subtitle_path = fetch_subtitles(yt_dlp_cmd, args.url, outtmpl, args.language)
            except subprocess.CalledProcessError:
                subtitle_path = None

        if subtitle_path:
            result = {
                "ok": True,
                "platform": args.platform,
                "url": args.url,
                "method": "subtitles",
                "transcript": read_subtitle_transcript(subtitle_path),
                "artifact": str(subtitle_path),
            }
            if args.write_markdown and args.output_dir:
                result["markdown_path"] = str(write_markdown_note(Path(args.output_dir), result, metadata))
            print(json.dumps(result, ensure_ascii=False))
            return 0

        audio_path = download_audio(yt_dlp_cmd, args.url, outtmpl)
        transcript_path = transcribe_audio(transcriber, transcriber_cmd, audio_path, args.language, workdir)
        result = {
            "ok": True,
            "platform": args.platform,
            "url": args.url,
            "method": f"{yt_dlp_name}+audio+{transcriber}",
            "transcript": read_text_file(transcript_path),
            "artifact": str(transcript_path),
        }
        if args.write_markdown and args.output_dir:
            result["markdown_path"] = str(write_markdown_note(Path(args.output_dir), result, metadata))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except subprocess.CalledProcessError as exc:
        result = {
            "ok": False,
            "platform": args.platform,
            "url": args.url,
            "error": exc.stderr.strip() or exc.stdout.strip() or "command failed",
        }
        print(json.dumps(result, ensure_ascii=False))
        return exc.returncode or 1
    except Exception as exc:  # pragma: no cover - defensive user-facing path
        print(json.dumps({"ok": False, "platform": args.platform, "url": args.url, "error": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        if args.keep_temp:
            print(json.dumps({"ok": True, "temp_dir": str(workdir)}, ensure_ascii=False), file=sys.stderr)
        else:
            workdir_cm.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
