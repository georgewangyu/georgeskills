#!/usr/bin/env python3
"""Refresh a media-root current-week symlink for weekly video batches."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


BATCH_RE = re.compile(r"^(?P<year>\d{4})-W(?P<week>\d{2})_video-batch$")


def parse_batch_key(path: Path) -> tuple[int, int]:
    match = BATCH_RE.match(path.name)
    if not match:
        raise ValueError(f"not a YYYY-Www_video-batch directory: {path}")
    return int(match.group("year")), int(match.group("week"))


def find_latest_batch(media_root: Path) -> Path:
    batch_root = media_root / "batches"
    if not batch_root.is_dir():
        raise NotADirectoryError(f"batch root does not exist: {batch_root}")

    candidates: list[Path] = []
    for year_dir in batch_root.iterdir():
        if not year_dir.is_dir():
            continue
        for batch_dir in year_dir.iterdir():
            if batch_dir.is_dir() and BATCH_RE.match(batch_dir.name):
                candidates.append(batch_dir)

    if not candidates:
        raise FileNotFoundError(f"no YYYY-Www_video-batch folders under {batch_root}")

    return max(candidates, key=parse_batch_key)


def resolve_batch_dir(media_root: Path, batch_dir: Path | None) -> Path:
    if batch_dir is None:
        return find_latest_batch(media_root).resolve()

    expanded = batch_dir.expanduser()
    if not expanded.is_absolute():
        expanded = media_root / expanded
    resolved = expanded.resolve()
    if not resolved.is_dir():
        raise NotADirectoryError(f"batch directory does not exist: {resolved}")
    parse_batch_key(resolved)
    return resolved


def link_target_for(link_path: Path, batch_dir: Path, absolute: bool) -> str:
    if absolute:
        return str(batch_dir)
    return os.path.relpath(batch_dir, start=link_path.parent)


def refresh_link(link_path: Path, target: str, dry_run: bool) -> None:
    if link_path.exists() and not link_path.is_symlink():
        raise FileExistsError(
            f"refusing to replace non-symlink current-week path: {link_path}"
        )

    if dry_run:
        action = "would update" if link_path.is_symlink() else "would create"
        print(f"{action}: {link_path} -> {target}")
        return

    if link_path.is_symlink():
        link_path.unlink()
    link_path.symlink_to(target, target_is_directory=True)
    print(f"updated: {link_path} -> {target}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Point <media-root>/_CURRENT_WEEK at the latest or selected weekly video batch."
    )
    parser.add_argument("--media-root", required=True, type=Path)
    parser.add_argument(
        "--batch-dir",
        type=Path,
        help="Batch folder to link. Defaults to the newest YYYY-Www_video-batch under media-root/batches.",
    )
    parser.add_argument("--link-name", default="_CURRENT_WEEK")
    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Use an absolute symlink target instead of a media-root-relative target.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    media_root = args.media_root.expanduser().resolve()
    if not media_root.is_dir():
        raise NotADirectoryError(f"media root does not exist: {media_root}")

    batch_dir = resolve_batch_dir(media_root, args.batch_dir)
    link_path = media_root / args.link_name
    target = link_target_for(link_path, batch_dir, args.absolute)
    refresh_link(link_path, target, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
