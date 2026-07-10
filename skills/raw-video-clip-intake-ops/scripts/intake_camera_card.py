#!/usr/bin/env python3
"""Inventory and copy camera-card clips into video project folders."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
DEFAULT_SIDECAR_EXTS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".wav",
    ".lrf",
    ".srt",
    ".thm",
    ".json",
}


@dataclass
class Clip:
    stem: str
    clip_id: str
    files: list[Path]
    video: Path | None
    duration: float | None
    size: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory and copy camera-card clips into project folders."
    )
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--batch-dir", type=Path)
    parser.add_argument("--groups-json", type=Path)
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument(
        "--copy-mode",
        choices=("copy", "hardlink"),
        default="copy",
        help="How to place files in project raw folders. Default: copy.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def clip_id_from_stem(stem: str) -> str:
    parts = stem.split("_")
    for part in parts:
        if len(part) == 4 and part.isdigit():
            return part
    return stem


def run_ffprobe_duration(path: Path) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def inventory(source_dir: Path) -> dict[str, Clip]:
    if not source_dir.is_dir():
        raise SystemExit(f"source dir not found: {source_dir}")

    stems: dict[str, list[Path]] = {}
    for path in sorted(source_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in DEFAULT_SIDECAR_EXTS:
            continue
        stems.setdefault(path.stem, []).append(path)

    clips: dict[str, Clip] = {}
    for stem, files in stems.items():
        video = next((p for p in files if p.suffix.lower() in VIDEO_EXTS), None)
        duration = run_ffprobe_duration(video) if video else None
        size = sum(p.stat().st_size for p in files)
        clip = Clip(
            stem=stem,
            clip_id=clip_id_from_stem(stem),
            files=sorted(files),
            video=video,
            duration=duration,
            size=size,
        )
        clips[clip.clip_id] = clip
    return dict(sorted(clips.items()))


def format_duration(duration: float | None) -> str:
    if duration is None:
        return "unknown"
    return f"{duration:.1f}s"


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{size}B"


def print_inventory(clips: dict[str, Clip]) -> None:
    print("clip_id\tstem\tduration\tfiles\tsize")
    for clip in clips.values():
        print(
            f"{clip.clip_id}\t{clip.stem}\t{format_duration(clip.duration)}\t"
            f"{len(clip.files)}\t{human_size(clip.size)}"
        )


def load_groups(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    groups = data.get("groups")
    if not isinstance(groups, list):
        raise SystemExit("groups-json must contain a top-level 'groups' list")
    for group in groups:
        if not group.get("slug") or not group.get("clip_ids"):
            raise SystemExit("each group must include 'slug' and 'clip_ids'")
    return groups


def ensure_project_dirs(project_dir: Path, dry_run: bool) -> None:
    for name in ("raw", "assets", "editor-projects", "exports", "final-videos"):
        path = project_dir / name
        if dry_run:
            print(f"[dry-run] mkdir -p {path}")
        else:
            path.mkdir(parents=True, exist_ok=True)


def place_file(src: Path, dest: Path, copy_mode: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] {copy_mode} {src} -> {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    if copy_mode == "hardlink":
        os.link(src, dest)
    else:
        shutil.copy2(src, dest)


def manifest_text(
    source_dir: Path,
    project_dir: Path,
    group: dict[str, Any],
    selected: list[Clip],
    copy_mode: str,
) -> str:
    title = group.get("title") or group["slug"].replace("-", " ").replace("_", " ")
    notes = group.get("notes") or {}
    uncertainty = group.get("uncertainty") or ""

    lines = [
        f"# Intake - {title}",
        "",
        "Source folder:",
        f"`{source_dir}`",
        "",
        "Copied to:",
        f"`{project_dir / 'raw'}`",
        "",
        f"Copy mode: `{copy_mode}`",
        "",
        "Original source files were left in place.",
        "",
        "## Clip Group",
        "",
        "| Clip | Duration | Files | Size | Notes |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for clip in selected:
        note = notes.get(clip.clip_id) or notes.get(clip.stem) or ""
        lines.append(
            f"| `{clip.stem}` | {format_duration(clip.duration)} | "
            f"{len(clip.files)} | {human_size(clip.size)} | {note} |"
        )
    if uncertainty:
        lines.extend(["", "## Uncertainty", "", str(uncertainty)])
    lines.append("")
    return "\n".join(lines)


def apply_groups(
    source_dir: Path,
    batch_dir: Path,
    clips: dict[str, Clip],
    groups: list[dict[str, Any]],
    copy_mode: str,
    dry_run: bool,
) -> None:
    if not batch_dir:
        raise SystemExit("--batch-dir is required when using --groups-json")

    for group in groups:
        project_dir = batch_dir / group["slug"]
        ensure_project_dirs(project_dir, dry_run)

        selected: list[Clip] = []
        for clip_id in group["clip_ids"]:
            clip = clips.get(str(clip_id))
            if not clip:
                raise SystemExit(f"clip id not found in source inventory: {clip_id}")
            selected.append(clip)
            for src in clip.files:
                place_file(src, project_dir / "raw" / src.name, copy_mode, dry_run)

        manifest = manifest_text(source_dir, project_dir, group, selected, copy_mode)
        manifest_path = project_dir / "INTAKE.md"
        if dry_run:
            print(f"[dry-run] write {manifest_path}")
        else:
            manifest_path.write_text(manifest)
        print(
            f"{group['slug']}: {len(selected)} clips, "
            f"{sum(len(c.files) for c in selected)} files, "
            f"{human_size(sum(c.size for c in selected))}"
        )


def create_contact_sheet(clips: dict[str, Clip], out: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required for --contact-sheet")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        raise SystemExit("Pillow is required for --contact-sheet") from exc

    tmp = out.parent / f".{out.stem}-frames"
    tmp.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    for clip in clips.values():
        if not clip.video:
            continue
        for label, args in (
            ("start", ["-ss", "1", "-i", str(clip.video)]),
            ("end", ["-sseof", "-1", "-i", str(clip.video)]),
        ):
            frame = tmp / f"{clip.clip_id}_{label}.jpg"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    *args,
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=240:-1",
                    str(frame),
                ],
                check=False,
            )
            if frame.exists():
                frames.append(frame)

    if not frames:
        raise SystemExit("no frames were generated")

    thumb_w, thumb_h, label_h, pad, cols = 220, 392, 42, 12, 4
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new(
        "RGB", (cols * (thumb_w + pad) + pad, rows * (thumb_h + label_h + pad) + pad), "white"
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, frame in enumerate(frames):
        image = Image.open(frame).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = pad + (idx % cols) * (thumb_w + pad)
        y = pad + (idx // cols) * (thumb_h + label_h + pad)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x, y + thumb_h + 4), frame.stem, fill="black", font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    print(f"contact sheet: {out}")


def main() -> int:
    args = parse_args()
    clips = inventory(args.source_dir)

    if args.inventory or not args.groups_json:
        print_inventory(clips)

    if args.contact_sheet:
        create_contact_sheet(clips, args.contact_sheet)

    if args.groups_json:
        groups = load_groups(args.groups_json)
        dry_run = not args.apply
        apply_groups(
            args.source_dir,
            args.batch_dir,
            clips,
            groups,
            args.copy_mode,
            dry_run,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
