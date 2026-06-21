#!/usr/bin/env python3
"""Normalize short-form final exports into project folders and a final index."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


VIDEO_EXTS = {".mp4", ".mov", ".m4v"}


def load_mapping(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("mapping must be a JSON object")
    if not isinstance(data.get("items"), list):
        raise ValueError("mapping must contain an items array")
    return data


def resolve_child(base: Path | None, value: str, label: str) -> Path:
    raw = Path(value).expanduser()
    if raw.is_absolute():
        return raw
    if base is None:
        raise ValueError(f"{label} is relative but no base directory was provided")
    return base / raw


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


def ensure_parent(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def plan_item(
    item: dict[str, Any],
    incoming_dir: Path | None,
    batch_dir: Path | None,
    final_index_dir: Path,
    final_subdir: str,
) -> dict[str, Path]:
    source_value = item.get("source")
    project_value = item.get("project")
    canonical_name = item.get("canonical_name")
    if not all(isinstance(v, str) and v for v in [source_value, project_value]):
        raise ValueError("each item requires non-empty source and project strings")

    source = resolve_child(incoming_dir, source_value, "source")
    project_dir = resolve_child(batch_dir, project_value, "project")

    if canonical_name is None:
        ext = source.suffix.lower()
        if ext not in VIDEO_EXTS:
            raise ValueError(f"cannot infer canonical name for non-video source: {source}")
        canonical_name = f"{project_dir.name}_final_v01{ext}"
    if not isinstance(canonical_name, str) or "/" in canonical_name:
        raise ValueError("canonical_name must be a filename, not a path")

    final_path = project_dir / final_subdir / canonical_name
    index_path = final_index_dir / canonical_name
    return {"source": source, "final": final_path, "index": index_path}


def apply_item(
    paths: dict[str, Path],
    source_action: str,
    index_mode: str,
    overwrite: bool,
    dry_run: bool,
) -> list[dict[str, str]]:
    source = paths["source"]
    final_path = paths["final"]
    index_path = paths["index"]
    actions: list[dict[str, str]] = []

    if not source.exists():
        raise FileNotFoundError(f"source does not exist: {source}")
    if source.suffix.lower() not in VIDEO_EXTS:
        raise ValueError(f"source is not a recognized video export: {source}")

    if final_path.exists() and not overwrite:
        raise FileExistsError(f"final target exists: {final_path}")
    if index_path.exists() or index_path.is_symlink():
        if not overwrite:
            raise FileExistsError(f"index target exists: {index_path}")

    actions.append({"action": source_action, "from": str(source), "to": str(final_path)})
    actions.append({"action": f"index:{index_mode}", "from": str(final_path), "to": str(index_path)})

    if dry_run:
        return actions

    ensure_parent(final_path, dry_run=False)
    if final_path.exists():
        final_path.unlink()
    if source_action == "move":
        shutil.move(str(source), str(final_path))
    elif source_action == "clone":
        clone_or_copy(source, final_path)
    elif source_action == "copy":
        shutil.copy2(source, final_path)
    else:
        raise ValueError(f"unsupported source action: {source_action}")

    ensure_parent(index_path, dry_run=False)
    if index_path.exists() or index_path.is_symlink():
        if index_path.is_dir() and not index_path.is_symlink():
            raise IsADirectoryError(f"index target is a directory: {index_path}")
        index_path.unlink()

    if index_mode == "symlink":
        index_path.symlink_to(relative_symlink_target(final_path, index_path))
    elif index_mode == "clone":
        clone_or_copy(final_path, index_path)
    elif index_mode == "copy":
        shutil.copy2(final_path, index_path)
    else:
        raise ValueError(f"unsupported index mode: {index_mode}")

    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True, type=Path, help="Path to mapping JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions only")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing final/index files")
    parser.add_argument(
        "--source-action",
        choices=["move", "clone", "copy"],
        default="move",
        help="How to place incoming exports into project final folders",
    )
    parser.add_argument(
        "--index-mode",
        choices=["symlink", "clone", "copy"],
        default="symlink",
        help="How to populate the quick-access final index",
    )
    parser.add_argument(
        "--final-subdir",
        default="final-videos",
        help="Project subdirectory that owns final renders",
    )
    args = parser.parse_args()

    mapping = load_mapping(args.mapping.expanduser())
    incoming_dir = Path(mapping["incoming_dir"]).expanduser() if mapping.get("incoming_dir") else None
    batch_dir = Path(mapping["batch_dir"]).expanduser() if mapping.get("batch_dir") else None
    final_index_value = mapping.get("final_index_dir")
    if not isinstance(final_index_value, str) or not final_index_value:
        raise ValueError("mapping requires final_index_dir")
    final_index_dir = Path(final_index_value).expanduser()

    all_actions: list[dict[str, str]] = []
    for item in mapping["items"]:
        if not isinstance(item, dict):
            raise ValueError("each mapping item must be an object")
        paths = plan_item(item, incoming_dir, batch_dir, final_index_dir, args.final_subdir)
        actions = apply_item(
            paths,
            source_action=args.source_action,
            index_mode=args.index_mode,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        all_actions.extend(actions)

    print(json.dumps({"dry_run": args.dry_run, "actions": all_actions}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
