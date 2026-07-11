#!/usr/bin/env python3
"""Safely migrate a legacy CapCut draft folder to a canonical project name."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts-root", required=True, type=Path)
    parser.add_argument("--current-name", required=True)
    parser.add_argument("--canonical-name", required=True)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--backup-root", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def fail(message: str) -> "NoReturn":
    raise RuntimeError(message)


def capcut_is_open() -> bool:
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["osascript", "-e", 'application "CapCut" is running'],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or result.stdout.strip().lower() not in {"true", "false"}:
            fail("Could not verify whether CapCut is open; refusing migration")
        return result.stdout.strip().lower() == "true"
    try:
        result = subprocess.run(
            ["pgrep", "-x", "CapCut"], check=False, capture_output=True, text=True
        )
    except FileNotFoundError:
        fail("Could not verify whether CapCut is open; refusing migration")
    return result.returncode == 0


def replace_path_values(value: Any, old_path: str, new_path: str) -> tuple[Any, int]:
    if isinstance(value, str):
        count = value.count(old_path)
        return value.replace(old_path, new_path), count
    if isinstance(value, list):
        total = 0
        output = []
        for item in value:
            replaced, count = replace_path_values(item, old_path, new_path)
            output.append(replaced)
            total += count
        return output, total
    if isinstance(value, dict):
        total = 0
        output = {}
        for key, item in value.items():
            replaced, count = replace_path_values(item, old_path, new_path)
            output[key] = replaced
            total += count
        return output, total
    return value, 0


def draft_path_aliases(source: Path) -> list[str]:
    aliases = {str(source)}
    meta_path = source / "draft_meta_info.json"
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return sorted(aliases)
    stored_path = metadata.get("draft_fold_path") if isinstance(metadata, dict) else None
    if isinstance(stored_path, str) and stored_path:
        aliases.add(stored_path)
    return sorted(aliases)


def json_change_plan(
    source: Path, target: Path, current_name: str, canonical_name: str
) -> list[dict[str, Any]]:
    old_paths = draft_path_aliases(source)
    new_path = str(target)
    changes: list[dict[str, Any]] = []
    meta_found = False
    for json_path in sorted(source.rglob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        replaced = data
        replacements = 0
        for old_path in old_paths:
            replaced, count = replace_path_values(replaced, old_path, new_path)
            replacements += count
        relative = json_path.relative_to(source)
        name_changed = False
        if relative == Path("draft_meta_info.json"):
            meta_found = True
            if not isinstance(replaced, dict):
                fail("draft_meta_info.json is not a JSON object")
            if replaced.get("draft_name") != current_name:
                fail(
                    "draft_meta_info.json name does not match requested current name: "
                    f"{replaced.get('draft_name')!r}"
                )
            replaced["draft_name"] = canonical_name
            replaced["draft_fold_path"] = new_path
            name_changed = True
        if replacements or name_changed:
            changes.append(
                {
                    "relative_path": str(relative),
                    "path_replacements": replacements,
                    "name_changed": name_changed,
                    "data": replaced,
                }
            )
    if not meta_found:
        fail("draft_meta_info.json was not found")
    return changes


def write_changes(stage: Path, changes: list[dict[str, Any]]) -> None:
    for change in changes:
        path = stage / change["relative_path"]
        temporary = path.with_suffix(f"{path.suffix}.codex-tmp")
        temporary.write_text(
            f"{json.dumps(change['data'], ensure_ascii=False, separators=(',', ':'))}\n",
            encoding="utf-8",
        )
        temporary.replace(path)


def validate_stage(
    stage: Path, canonical_name: str, target: Path, old_paths: list[str]
) -> None:
    meta_path = stage / "draft_meta_info.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("draft_name") != canonical_name:
        fail("Staged draft name validation failed")
    if meta.get("draft_fold_path") != str(target):
        fail("Staged draft path validation failed")
    for json_path in stage.rglob("*.json"):
        try:
            content = json_path.read_text(encoding="utf-8")
            for old_path in old_paths:
                if old_path in content:
                    fail(f"Staged JSON still references the old draft path: {json_path}")
        except (OSError, UnicodeDecodeError):
            continue


def run() -> dict[str, Any]:
    args = parse_args()
    drafts_root = args.drafts_root.expanduser().resolve()
    project_dir = args.project_dir.expanduser().resolve()
    backup_root = args.backup_root.expanduser().resolve()
    canonical_name = args.canonical_name
    current_name = args.current_name

    if not PROJECT_NAME_RE.fullmatch(canonical_name):
        fail(f"Canonical name is not YYYY-MM-DD_video-slug: {canonical_name}")
    if project_dir.name != canonical_name or not project_dir.is_dir():
        fail("Project directory must exist and match the canonical name")
    if not drafts_root.is_dir():
        fail(f"Drafts root does not exist: {drafts_root}")
    source = drafts_root / current_name
    target = drafts_root / canonical_name
    if not source.is_dir():
        fail(f"Current draft does not exist: {source}")
    if target.exists():
        fail(f"Canonical target already exists: {target}")
    if (source / ".locked").exists():
        fail(f"Draft has a .locked marker; refusing migration: {source}")

    is_open = capcut_is_open()
    if args.apply and is_open:
        fail("CapCut is open; close it before applying draft migration")

    changes = json_change_plan(source, target, current_name, canonical_name)
    changed_files = [
        {
            "relative_path": change["relative_path"],
            "path_replacements": change["path_replacements"],
            "name_changed": change["name_changed"],
        }
        for change in changes
    ]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_root / f"{current_name}__to__{canonical_name}__{timestamp}"
    receipt_path = project_dir / "editor-projects" / "capcut-draft-migration.json"
    output = {
        "mode": "dry-run" if args.dry_run else "apply",
        "current_draft": str(source),
        "canonical_draft": str(target),
        "backup_path": str(backup_path),
        "receipt_path": str(receipt_path),
        "capcut_open": is_open,
        "changed_json_files": changed_files,
    }
    if args.dry_run:
        return output

    backup_root.mkdir(parents=True, exist_ok=True)
    if os.stat(drafts_root).st_dev != os.stat(backup_root).st_dev:
        fail("Backup root must be on the same filesystem for an atomic source move")
    if backup_path.exists():
        fail(f"Backup path already exists: {backup_path}")
    stage = drafts_root / f".{canonical_name}.codex-staging-{os.getpid()}"
    if stage.exists():
        fail(f"Staging path already exists: {stage}")

    try:
        shutil.copytree(source, stage, symlinks=True)
        write_changes(stage, changes)
        validate_stage(stage, canonical_name, target, draft_path_aliases(source))
        source.rename(backup_path)
        try:
            stage.rename(target)
        except Exception:
            backup_path.rename(source)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        **output,
        "status": "migrated",
        "migrated_at": datetime.now(timezone.utc).isoformat(),
    }
    temporary = receipt_path.with_suffix(".json.tmp")
    temporary.write_text(f"{json.dumps(receipt, indent=2)}\n", encoding="utf-8")
    temporary.replace(receipt_path)
    output["status"] = "migrated"
    return output


if __name__ == "__main__":
    try:
        print(json.dumps(run(), indent=2))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
