#!/usr/bin/env python3
"""Create a new Manim Community explainer project from the bundled scaffold."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "manim-project"
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def project_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise argparse.ArgumentTypeError("project name must contain a letter or digit")
    return slug


def scene_class(value: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("scene class must be a valid Python identifier")
    return value


def substitutions(args: argparse.Namespace) -> dict[str, str]:
    return {
        "__PROJECT_NAME__": args.project_name,
        "__SCENE_CLASS__": args.scene_class,
        "__SCENE_TITLE_JSON__": json.dumps(args.title),
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
        if "__PROJECT_NAME__" in text or "__SCENE_CLASS__" in text or "__SCENE_TITLE_JSON__" in text:
            raise RuntimeError(f"unresolved placeholder in {source}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        shutil.copymode(source, target)
        written.append(target)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project-name", required=True, type=project_slug)
    parser.add_argument("--scene-class", default="MechanismExplainer", type=scene_class)
    parser.add_argument("--title", default="Input to output")
    return parser.parse_args()


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
