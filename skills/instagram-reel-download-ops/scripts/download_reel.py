#!/usr/bin/env python3
"""Download one public Instagram Reel and verify the resulting MP4."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


SHORTCODE = re.compile(r"[A-Za-z0-9_-]+")


def normalize_reel_url(value: str) -> tuple[str, str]:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in {"instagram.com", "www.instagram.com"}:
        raise ValueError("Expected an https://www.instagram.com/reel/<shortcode>/ URL")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Unexpected URL authority")
    parts = parsed.path.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "reel" or not SHORTCODE.fullmatch(parts[1]):
        raise ValueError("Expected an Instagram Reel URL with one shortcode")
    return f"https://www.instagram.com/reel/{parts[1]}/", parts[1]


def downloader_command() -> list[str]:
    installed = shutil.which("yt-dlp")
    if installed:
        return [installed]
    uv = shutil.which("uv")
    if uv:
        return [uv, "tool", "run", "--from", "yt-dlp", "yt-dlp"]
    raise RuntimeError("Install yt-dlp or uv to download a Reel")


def media_info(path: Path) -> dict:
    probe = shutil.which("ffprobe")
    if not probe:
        raise RuntimeError("ffprobe is required to validate the downloaded video")
    result = subprocess.run(
        [probe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    videos = [stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"]
    duration = float(data.get("format", {}).get("duration", 0))
    if not videos or duration <= 0 or path.stat().st_size == 0:
        raise RuntimeError("Downloaded file has no valid video stream or duration")
    return {"duration_seconds": duration, "width": videos[0].get("width"), "height": videos[0].get("height")}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, output_dir: Path) -> dict:
    canonical_url, shortcode = normalize_reel_url(url)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{shortcode}.mp4"
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    with tempfile.TemporaryDirectory(prefix=".instagram-reel-", dir=output_dir) as temp:
        temporary = Path(temp)
        command = downloader_command() + [
            "--ignore-config", "--no-playlist", "--no-overwrites",
            "--no-write-info-json", "--no-write-thumbnail",
            "--format", "bv*+ba/b", "--merge-output-format", "mp4",
            "--output", str(temporary / "reel.%(ext)s"), canonical_url,
        ]
        subprocess.run(command, check=True)
        candidates = [p for p in temporary.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"]
        if len(candidates) != 1:
            raise RuntimeError("Downloader did not produce exactly one MP4")
        info = media_info(candidates[0])
        digest = sha256(candidates[0])
        # Same-directory hard linking publishes the verified file atomically.
        # It fails if another download created this destination meanwhile.
        os.link(candidates[0], destination)
        return {"source_url": canonical_url, "path": str(destination.resolve()), "size_bytes": destination.stat().st_size, "sha256": digest, **info}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Public https://www.instagram.com/reel/<shortcode>/ URL")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(download(args.url, args.output_dir.expanduser().resolve()), indent=2))
        return 0
    except (ValueError, RuntimeError, FileExistsError, subprocess.CalledProcessError, OSError) as error:
        print(f"Download failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
