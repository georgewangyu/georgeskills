#!/usr/bin/env python3
"""Refresh a weekly phone-transfer bundle from project final media files."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_EXTS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".png",
    ".jpg",
    ".jpeg",
    ".heic",
}


def relative_symlink_target(target: Path, link_path: Path) -> str:
    return os.path.relpath(target, start=link_path.parent)


def clone_or_copy(source: Path, target: Path) -> None:
    if sys.platform == "darwin":
        result = subprocess.run(
            ["cp", "-c", str(source), str(target)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return
    shutil.copy2(source, target)


def collect_final_files(batch_dir: Path, final_subdir: str, exts: set[str]) -> list[Path]:
    files: list[Path] = []
    for project_dir in sorted(path for path in batch_dir.iterdir() if path.is_dir()):
        final_dir = project_dir / final_subdir
        if not final_dir.is_dir():
            continue
        for path in sorted(final_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in exts:
                files.append(path)
    return files


def place_link(source: Path, target: Path, mode: str) -> None:
    if mode == "hardlink":
        os.link(source, target)
    elif mode == "symlink":
        target.symlink_to(relative_symlink_target(source, target))
    elif mode == "clone":
        clone_or_copy(source, target)
    elif mode == "copy":
        shutil.copy2(source, target)
    else:
        raise ValueError(f"unsupported link mode: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", required=True, type=Path)
    parser.add_argument("--transfer-dir", required=True, type=Path)
    parser.add_argument("--final-subdir", default="final-videos")
    parser.add_argument(
        "--ext",
        action="append",
        default=[],
        help="Additional or replacement extension. Repeatable. Defaults include common video/image finals.",
    )
    parser.add_argument(
        "--link-mode",
        choices=["hardlink", "symlink", "clone", "copy"],
        default="hardlink",
        help="How to populate the transfer bundle. Hardlinks are Finder-friendly and space-efficient on one volume.",
    )
    parser.add_argument("--clean", action="store_true", help="Remove stale files/links from the transfer directory")
    parser.add_argument("--overwrite", action="store_true", help="Replace conflicting transfer entries")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions only")
    args = parser.parse_args()

    batch_dir = args.batch_dir.expanduser()
    transfer_dir = args.transfer_dir.expanduser()
    exts = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in args.ext} or DEFAULT_EXTS

    if not batch_dir.is_dir():
        raise NotADirectoryError(f"batch directory does not exist: {batch_dir}")

    sources = collect_final_files(batch_dir, args.final_subdir, exts)
    desired = {source.name: source for source in sources}
    if len(desired) != len(sources):
        names = [source.name for source in sources]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise ValueError(f"duplicate final filenames would collide in transfer bundle: {duplicates}")

    actions: list[dict[str, str]] = []

    if args.clean and transfer_dir.exists():
        for existing in sorted(transfer_dir.iterdir()):
            if existing.name not in desired:
                actions.append({"action": "remove-stale", "path": str(existing)})
                if not args.dry_run:
                    if existing.is_dir() and not existing.is_symlink():
                        raise IsADirectoryError(f"stale entry is a directory: {existing}")
                    existing.unlink()

    for filename, source in desired.items():
        target = transfer_dir / filename
        if target.exists() or target.is_symlink():
            try:
                if target.samefile(source):
                    actions.append({"action": "keep", "from": str(source), "to": str(target)})
                    continue
            except FileNotFoundError:
                pass
            if not args.overwrite:
                raise FileExistsError(f"transfer target exists: {target}")
            actions.append({"action": "replace", "from": str(source), "to": str(target)})
            if not args.dry_run:
                if target.is_dir() and not target.is_symlink():
                    raise IsADirectoryError(f"transfer target is a directory: {target}")
                target.unlink()
        else:
            actions.append({"action": args.link_mode, "from": str(source), "to": str(target)})

        if not args.dry_run:
            transfer_dir.mkdir(parents=True, exist_ok=True)
            place_link(source, target, args.link_mode)

    print(json.dumps({"dry_run": args.dry_run, "actions": actions}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
