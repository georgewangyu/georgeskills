#!/usr/bin/env python3
"""Inspect common image assets without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    return None


def gif_dimensions(data: bytes) -> tuple[int, int] | None:
    if data[:6] in {b"GIF87a", b"GIF89a"} and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    return None


def jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        length = struct.unpack(">H", data[index : index + 2])[0]
        if marker in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)):
            if index + 7 > len(data):
                return None
            height, width = struct.unpack(">HH", data[index + 3 : index + 7])
            return width, height
        index += max(length, 2)
    return None


def inspect(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    detected = "unknown"
    dimensions = None
    if png_dimensions(data):
        detected, dimensions = "png", png_dimensions(data)
    elif jpeg_dimensions(data):
        detected, dimensions = "jpeg", jpeg_dimensions(data)
    elif gif_dimensions(data):
        detected, dimensions = "gif", gif_dimensions(data)
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        detected = "webp"

    expected = "jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else path.suffix.lower().lstrip(".")
    problems = []
    if not data:
        problems.append("empty file")
    if detected == "unknown":
        problems.append("unrecognized image signature")
    if detected != "unknown" and expected != detected:
        problems.append(f"extension says {expected}, signature says {detected}")
    if dimensions and (dimensions[0] == 0 or dimensions[1] == 0):
        problems.append("zero dimensions")

    return {
        "file": path.name,
        "bytes": len(data),
        "detected_type": detected,
        "width": dimensions[0] if dimensions else None,
        "height": dimensions[1] if dimensions else None,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("assets_dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    files = sorted(p for p in args.assets_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    results = [inspect(path) for path in files]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for item in results:
            size = f"{item['width']}x{item['height']}" if item["width"] else "dimensions unavailable"
            problems = "; ".join(item["problems"]) if item["problems"] else "ok"
            print(f"{item['file']}: {item['detected_type']} {size}, {item['bytes']} bytes — {problems}")
    return 1 if any(item["problems"] for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
