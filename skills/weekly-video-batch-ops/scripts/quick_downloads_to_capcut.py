#!/usr/bin/env python3
"""Move recent Downloads clips into a weekly project and create a CapCut shell."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PROJECT_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9]+(?:-[a-z0-9]+)*$")
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v", ".avi", ".mkv"}
REQUIRED_CONFIG = {
    "downloads_dir",
    "current_week_link",
    "drafts_root",
    "empty_template",
    "capcutbot_dir",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fast-path recent Downloads clips into a named weekly project."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--max-age-minutes", type=int, default=60)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def fail(message: str) -> "NoReturn":
    raise RuntimeError(message)


def load_config(path: Path) -> dict[str, object]:
    config_path = path.expanduser().resolve()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Could not load intake config {config_path}: {error}")
    if not isinstance(payload, dict):
        fail("Intake config must be a JSON object")
    missing = sorted(REQUIRED_CONFIG - payload.keys())
    if missing:
        fail(f"Intake config is missing keys: {', '.join(missing)}")
    return payload


def config_path(config: dict[str, object], key: str) -> Path:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"Config value must be a nonempty path string: {key}")
    return Path(value).expanduser().resolve()


def resolve_batch(config: dict[str, object]) -> tuple[Path, Path]:
    raw_link = config.get("current_week_link")
    if not isinstance(raw_link, str) or not raw_link.strip():
        fail("Config value must be a nonempty path string: current_week_link")
    current_week = Path(raw_link).expanduser()
    if not current_week.is_absolute():
        current_week = Path.cwd() / current_week
    if not current_week.is_symlink():
        fail(f"Current-week path must be a symlink: {current_week}")
    batch_dir = current_week.resolve()
    if not batch_dir.is_dir():
        fail(f"Current-week symlink target is not a directory: {batch_dir}")
    return current_week, batch_dir


def recent_videos(downloads_dir: Path, count: int, max_age_minutes: int) -> list[Path]:
    if count < 1:
        fail("Clip count must be at least 1")
    if max_age_minutes < 1:
        fail("Maximum age must be at least 1 minute")
    if not downloads_dir.is_dir():
        fail(f"Downloads directory does not exist: {downloads_dir}")

    cutoff = time.time() - max_age_minutes * 60
    candidates = [
        path
        for path in downloads_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in VIDEO_EXTENSIONS
        and path.stat().st_mtime >= cutoff
    ]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if len(candidates) != count:
        names = ", ".join(path.name for path in candidates) or "none"
        fail(
            f"Expected exactly {count} recent Downloads videos within "
            f"{max_age_minutes} minutes; found {len(candidates)}: {names}"
        )
    return candidates


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_draft_wrapper(mode: str, project_dir: Path, config: dict[str, object]) -> dict:
    wrapper = Path(__file__).with_name("prepare_capcut_draft.py")
    empty_template = config.get("empty_template")
    if not isinstance(empty_template, str) or not empty_template.strip():
        fail("Config value must be a nonempty string: empty_template")
    command = [
        sys.executable,
        str(wrapper),
        "--project-dir",
        str(project_dir),
        "--drafts-root",
        str(config_path(config, "drafts_root")),
        "--empty-template",
        empty_template,
        "--capcutbot-dir",
        str(config_path(config, "capcutbot_dir")),
        f"--{mode}",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        fail(result.stderr.strip() or f"CapCut draft {mode} failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        fail(f"CapCut draft helper returned invalid JSON: {error}")


DraftRunner = Callable[[str, Path, dict[str, object]], dict]


def write_active_status(project_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    path = project_dir / "PROJECT_STATUS.json"
    payload = {
        "schema_version": 1,
        "project_name": project_dir.name,
        "canonical_project_dir": str(project_dir.resolve()),
        "status": "active",
        "carryover_eligible": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def execute(args: argparse.Namespace, draft_runner: DraftRunner = run_draft_wrapper) -> dict:
    started = time.monotonic()
    if not PROJECT_NAME_RE.fullmatch(args.project_name):
        fail(f"Project name is not canonical YYYY-MM-DD_video-slug: {args.project_name}")

    config = load_config(args.config)
    downloads_dir = config_path(config, "downloads_dir")
    current_week, batch_dir = resolve_batch(config)
    drafts_root = config_path(config, "drafts_root")
    clips = recent_videos(downloads_dir, args.count, args.max_age_minutes)
    project_dir = batch_dir / args.project_name
    draft_dir = drafts_root / args.project_name
    if project_dir.exists():
        fail(f"Project already exists; nothing was changed: {project_dir}")
    if draft_dir.exists():
        fail(f"CapCut draft already exists; nothing was changed: {draft_dir}")

    clip_plan = [
        {
            "source": str(path),
            "destination": str(project_dir / "raw" / path.name),
            "size": path.stat().st_size,
            "modified_at": path.stat().st_mtime,
        }
        for path in clips
    ]
    output = {
        "mode": "apply" if args.apply else "dry-run",
        "project_name": args.project_name,
        "current_week_link": str(current_week),
        "batch_dir": str(batch_dir),
        "project_dir": str(project_dir),
        "draft_dir": str(draft_dir),
        "clips": clip_plan,
    }
    with tempfile.TemporaryDirectory() as temporary:
        preview_project = Path(temporary) / args.project_name
        preview_project.mkdir()
        draft_dry_run = draft_runner("dry-run", preview_project, config)

    if args.dry_run:
        output["draft_dry_run"] = draft_dry_run
        output["elapsed_seconds"] = round(time.monotonic() - started, 3)
        return output

    source_hashes = {path.name: sha256(path) for path in clips}
    (project_dir / "raw").mkdir(parents=True)
    (project_dir / "assets").mkdir()

    moved: list[Path] = []
    for source in clips:
        destination = project_dir / "raw" / source.name
        shutil.move(str(source), str(destination))
        moved.append(destination)

    verification = []
    for destination in moved:
        source = downloads_dir / destination.name
        digest = sha256(destination)
        if source.exists():
            fail(f"Source still exists after move: {source}")
        if digest != source_hashes[destination.name]:
            fail(f"Hash mismatch after move: {destination}")
        verification.append(
            {"file": str(destination), "sha256": digest, "verified": True}
        )

    draft_apply = draft_runner("apply", project_dir, config)
    receipt = project_dir / "editor-projects" / "capcut-draft.json"
    if not receipt.is_file():
        fail(f"CapCut receipt missing after apply: {receipt}")
    status_file = write_active_status(project_dir)

    output.update(
        {
            "clip_verification": verification,
            "draft_dry_run": draft_dry_run,
            "draft_apply": draft_apply,
            "receipt": str(receipt),
            "status_file": str(status_file),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    )
    return output


if __name__ == "__main__":
    try:
        print(json.dumps(execute(parse_args()), indent=2))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
