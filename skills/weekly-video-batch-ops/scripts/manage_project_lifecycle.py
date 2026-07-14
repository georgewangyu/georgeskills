#!/usr/bin/env python3
"""Mark video projects and build non-destructive lifecycle views.

Canonical project directories never move. Status lives in PROJECT_STATUS.json;
_COMPLETED and _CARRYOVER contain symlinks only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_FILE = "PROJECT_STATUS.json"
PROJECT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_.+")
BATCH_RE = re.compile(r"^\d{4}-W\d{2}_video-batch$")
STATUSES = ("active", "completed", "dropped")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_status(project: Path) -> dict[str, Any] | None:
    path = project / STATUS_FILE
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    status = payload.get("status")
    if status not in STATUSES:
        raise RuntimeError(f"Invalid status in {path}: {status!r}")
    return payload


def validate_project(project: Path) -> Path:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise RuntimeError(f"Project directory does not exist: {project}")
    if not PROJECT_RE.match(project.name):
        raise RuntimeError(f"Project name is not canonical: {project.name}")
    if not BATCH_RE.match(project.parent.name):
        raise RuntimeError(f"Project is not directly inside a weekly batch: {project}")
    return project


def media_root_for(project: Path) -> Path:
    # <root>/batches/YYYY/YYYY-Www_video-batch/project
    if project.parent.parent.parent.name != "batches":
        raise RuntimeError(f"Could not infer media root from {project}")
    return project.parent.parent.parent.parent


def relative_target(link: Path, target: Path) -> str:
    return os.path.relpath(target, start=link.parent)


def plan_link(link: Path, target: Path, apply: bool) -> dict[str, str]:
    desired = relative_target(link, target)
    if link.is_symlink():
        current = os.readlink(link)
        if link.resolve(strict=False) == target.resolve():
            return {"action": "unchanged", "path": str(link), "target": current}
        if apply:
            link.unlink()
            link.symlink_to(desired)
        return {"action": "replace", "path": str(link), "target": desired}
    if link.exists():
        raise RuntimeError(f"Refusing to replace non-symlink lifecycle path: {link}")
    if apply:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(desired)
    return {"action": "create", "path": str(link), "target": desired}


def plan_unlink(link: Path, apply: bool) -> dict[str, str] | None:
    if not link.is_symlink():
        if link.exists():
            raise RuntimeError(f"Refusing to remove non-symlink lifecycle path: {link}")
        return None
    target = os.readlink(link)
    if apply:
        link.unlink()
    return {"action": "remove", "path": str(link), "target": target}


def write_status(
    project: Path, status: str, reason: str | None, apply: bool
) -> dict[str, Any]:
    project = validate_project(project)
    existing = read_status(project) or {}
    timestamp = now_iso()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "project_name": project.name,
        "canonical_project_dir": str(project),
        "status": status,
        "carryover_eligible": status == "active",
        "created_at": existing.get("created_at", timestamp),
        "updated_at": timestamp,
    }
    if reason:
        payload["reason"] = reason
    elif existing.get("reason") and existing.get("status") == status:
        payload["reason"] = existing["reason"]

    changes: list[dict[str, str]] = []
    completed_link = project.parent / "_COMPLETED" / project.name
    if status == "completed":
        changes.append(plan_link(completed_link, project, apply))
    else:
        removed = plan_unlink(completed_link, apply)
        if removed:
            changes.append(removed)

    media_root = media_root_for(project)
    for link in media_root.glob(f"batches/*/*_video-batch/_CARRYOVER/{project.name}"):
        removed = plan_unlink(link, apply)
        if removed:
            changes.append(removed)

    status_path = project / STATUS_FILE
    if apply:
        temporary = status_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, status_path)

    return {
        "mode": "apply" if apply else "dry-run",
        "status_file": str(status_path),
        "manifest": payload,
        "view_changes": changes,
    }


def batch_projects(batch: Path) -> list[Path]:
    if not batch.is_dir():
        return []
    return sorted(
        path
        for path in batch.iterdir()
        if path.is_dir() and not path.is_symlink() and PROJECT_RE.match(path.name)
    )


def weekly_batches(media_root: Path) -> list[Path]:
    batches = media_root / "batches"
    return sorted(
        path
        for year in batches.glob("[0-9][0-9][0-9][0-9]")
        for path in year.glob("*_video-batch")
        if path.is_dir() and BATCH_RE.match(path.name)
    )


def sync_view(
    view: Path, expected: dict[str, Path], apply: bool, create_empty: bool = False
) -> tuple[list[dict[str, str]], list[str]]:
    changes: list[dict[str, str]] = []
    conflicts: list[str] = []
    if apply and (expected or create_empty):
        view.mkdir(parents=True, exist_ok=True)
    if view.exists() and not view.is_dir():
        raise RuntimeError(f"Lifecycle view is not a directory: {view}")

    if view.is_dir():
        for child in sorted(view.iterdir()):
            if child.name in expected:
                continue
            if child.is_symlink():
                removed = plan_unlink(child, apply)
                if removed:
                    changes.append(removed)
            else:
                conflicts.append(str(child))

    for name, target in sorted(expected.items()):
        changes.append(plan_link(view / name, target, apply))
    return changes, conflicts


def refresh_views(
    media_root: Path, current_batch: Path, lookback_weeks: int, apply: bool
) -> dict[str, Any]:
    media_root = media_root.expanduser().resolve()
    current_batch = current_batch.expanduser().resolve()
    all_batches = weekly_batches(media_root)
    if current_batch not in all_batches:
        raise RuntimeError(f"Current batch is not under {media_root / 'batches'}: {current_batch}")
    current_index = all_batches.index(current_batch)
    start = max(0, current_index - lookback_weeks)
    scanned = all_batches[start : current_index + 1]

    carryover: dict[str, Path] = {}
    completed_by_batch: dict[Path, dict[str, Path]] = {}
    unclassified: list[str] = []
    dropped: list[str] = []

    for batch in scanned:
        completed_by_batch[batch] = {}
        for project in batch_projects(batch):
            manifest = read_status(project)
            if manifest is None:
                unclassified.append(str(project))
                continue
            status = manifest["status"]
            if status == "completed":
                completed_by_batch[batch][project.name] = project
            elif status == "dropped":
                dropped.append(str(project))
            elif batch != current_batch:
                if project.name in carryover:
                    raise RuntimeError(f"Duplicate carryover project name: {project.name}")
                carryover[project.name] = project

    changes: list[dict[str, str]] = []
    conflicts: list[str] = []
    for batch, expected in completed_by_batch.items():
        batch_changes, batch_conflicts = sync_view(
            batch / "_COMPLETED",
            expected,
            apply,
            create_empty=batch == current_batch,
        )
        changes.extend(batch_changes)
        conflicts.extend(batch_conflicts)

    carry_changes, carry_conflicts = sync_view(
        current_batch / "_CARRYOVER", carryover, apply, create_empty=True
    )
    changes.extend(carry_changes)
    conflicts.extend(carry_conflicts)

    return {
        "mode": "apply" if apply else "dry-run",
        "media_root": str(media_root),
        "current_batch": str(current_batch),
        "scanned_batches": [str(path) for path in scanned],
        "carryover_projects": [str(path) for path in carryover.values()],
        "completed_projects": [
            str(path)
            for expected in completed_by_batch.values()
            for path in expected.values()
        ],
        "dropped_projects": dropped,
        "unclassified_projects": unclassified,
        "view_changes": changes,
        "conflicts": conflicts,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set-status")
    set_parser.add_argument("--project", type=Path, required=True)
    set_parser.add_argument("--status", choices=STATUSES, required=True)
    set_parser.add_argument("--reason")
    set_mode = set_parser.add_mutually_exclusive_group(required=True)
    set_mode.add_argument("--dry-run", action="store_true")
    set_mode.add_argument("--apply", action="store_true")

    refresh_parser = subparsers.add_parser("refresh-views")
    refresh_parser.add_argument("--media-root", type=Path, required=True)
    refresh_parser.add_argument("--current-batch", type=Path, required=True)
    refresh_parser.add_argument("--lookback-weeks", type=int, default=8)
    refresh_mode = refresh_parser.add_mutually_exclusive_group(required=True)
    refresh_mode.add_argument("--dry-run", action="store_true")
    refresh_mode.add_argument("--apply", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "set-status":
        output = write_status(args.project, args.status, args.reason, args.apply)
    else:
        output = refresh_views(
            args.media_root, args.current_batch, args.lookback_weeks, args.apply
        )
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
