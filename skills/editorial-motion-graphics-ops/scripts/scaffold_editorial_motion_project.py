#!/usr/bin/env python3
"""Create a deterministic editorial-motion starter project."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "remotion-project"


def project_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise argparse.ArgumentTypeError("project name must contain a letter or digit")
    return slug


def title_text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise argparse.ArgumentTypeError("title must not be empty")
    if len(normalized) > 72:
        raise argparse.ArgumentTypeError("title must be 72 characters or fewer")
    return normalized


def bounded_int(label: str, minimum: int, maximum: int):
    def parse(value: str) -> int:
        parsed = int(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(
                f"{label} must be between {minimum} and {maximum}"
            )
        return parsed

    return parse


def bounded_float(label: str, minimum: float, maximum: float):
    def parse(value: str) -> float:
        parsed = float(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(
                f"{label} must be between {minimum} and {maximum}"
            )
        return parsed

    return parse


def substitutions(args: argparse.Namespace) -> dict[str, str]:
    duration_frames = round(args.duration_seconds * args.fps)
    duration_seconds = duration_frames / args.fps
    final_frame = duration_frames - 1
    frame_at = lambda fraction: min(final_frame, round(duration_frames * fraction))
    first_hold_end = frame_at(0.34)
    transformation_frame = frame_at(0.48)
    transformation_end = frame_at(0.70)
    final_reveal_start = frame_at(0.62)
    final_reveal_end = frame_at(0.84)
    poster_frame = min(duration_frames - 1, round(duration_frames * 0.88))
    final_clip = (
        "outputs/alpha.mov"
        if args.delivery_mode == "alpha-overlay"
        else "outputs/review.mp4"
    )
    render_command = (
        "npm run render:alpha"
        if args.delivery_mode == "alpha-overlay"
        else "npm run render:review"
    )
    return {
        "__PROJECT_NAME__": args.project_name,
        "__TITLE_JSON__": json.dumps(args.title),
        "__DURATION_SECONDS__": json.dumps(duration_seconds),
        "__DURATION_FRAMES__": str(duration_frames),
        "__FINAL_FRAME__": str(final_frame),
        "__FIRST_HOLD_END_FRAME__": str(first_hold_end),
        "__TRANSFORMATION_FRAME__": str(transformation_frame),
        "__TRANSFORMATION_END_FRAME__": str(transformation_end),
        "__FINAL_REVEAL_START_FRAME__": str(final_reveal_start),
        "__FINAL_REVEAL_END_FRAME__": str(final_reveal_end),
        "__OPENING_END_FRAME__": str(frame_at(0.18)),
        "__FOCUS_START_FRAME__": str(frame_at(0.28)),
        "__FOCUS_END_FRAME__": str(frame_at(0.56)),
        "__WORK_REVEAL_START_FRAME__": str(frame_at(0.04)),
        "__WORK_REVEAL_END_FRAME__": str(frame_at(0.20)),
        "__CARD_ENTRY_START_FRAME__": str(frame_at(0.06)),
        "__CARD_ENTRY_DURATION_FRAMES__": str(max(2, round(duration_frames * 0.14))),
        "__CARD_STAGGER_FRAMES__": str(max(1, round(duration_frames * 0.03))),
        "__SETTLE_START_FRAME__": str(frame_at(0.58)),
        "__POSTER_FRAME__": str(poster_frame),
        "__FPS__": str(args.fps),
        "__WIDTH__": str(args.width),
        "__HEIGHT__": str(args.height),
        "__DELIVERY_MODE_JSON__": json.dumps(args.delivery_mode),
        "__SAFE_LEFT__": str(round(args.width * 0.085)),
        "__SAFE_RIGHT__": str(round(args.width * 0.915)),
        "__SAFE_TOP__": str(round(args.height * 0.09)),
        "__SAFE_BOTTOM__": str(round(args.height * 0.87)),
        "__FINAL_CLIP_JSON__": json.dumps(final_clip),
        "__RENDER_COMMAND_JSON__": json.dumps(render_command),
    }


def scaffold(args: argparse.Namespace) -> list[Path]:
    destination = args.output.expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(f"refusing to write into non-empty directory: {destination}")

    destination.mkdir(parents=True, exist_ok=True)
    replacements = substitutions(args)
    written: list[Path] = []

    for source in sorted(TEMPLATE_ROOT.rglob("*")):
        relative = source.relative_to(TEMPLATE_ROOT)
        target = destination / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if source.is_symlink():
            raise RuntimeError(f"template symlinks are not supported: {source}")

        text = source.read_text(encoding="utf-8")
        for placeholder, replacement in replacements.items():
            text = text.replace(placeholder, replacement)
        unresolved = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]+__", text)))
        if unresolved:
            raise RuntimeError(f"unresolved placeholders in {source}: {unresolved}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        shutil.copymode(source, target)
        written.append(target)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project-name", required=True, type=project_slug)
    parser.add_argument(
        "--title",
        default="One view, many active lanes",
        type=title_text,
    )
    parser.add_argument(
        "--duration-seconds",
        default=4.0,
        type=bounded_float("duration", 1.0, 30.0),
    )
    parser.add_argument("--fps", default=30, type=bounded_int("fps", 12, 60))
    parser.add_argument("--width", default=1080, type=bounded_int("width", 240, 4096))
    parser.add_argument("--height", default=1920, type=bounded_int("height", 240, 4096))
    parser.add_argument(
        "--delivery-mode",
        choices=("alpha-overlay", "full-screen"),
        default="alpha-overlay",
    )
    args = parser.parse_args()
    if abs((args.width / args.height) - (9 / 16)) > 0.001:
        parser.error(
            "the bundled starter uses a 9:16 design space; choose a 9:16 "
            "resolution or redesign the generated composition for another aspect ratio"
        )
    return args


def main() -> int:
    args = parse_args()
    try:
        written = scaffold(args)
    except (OSError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Created {len(written)} files in {args.output.expanduser().resolve()}")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
