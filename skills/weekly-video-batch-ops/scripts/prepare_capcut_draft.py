#!/usr/bin/env python3
"""Safely create a canonically named empty CapCut draft and project receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9]+(?:-[a-z0-9]+)*$")
DRAFT_FILENAMES = ("draft_info.json", "draft_content.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Duplicate a verified empty CapCut template without overwriting editor state."
    )
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--drafts-root", required=True, type=Path)
    parser.add_argument("--empty-template", required=True)
    parser.add_argument("--capcutbot-dir", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def fail(message: str) -> "NoReturn":
    raise RuntimeError(message)


def find_draft_file(project_dir: Path) -> Path:
    for filename in DRAFT_FILENAMES:
        candidate = project_dir / filename
        if candidate.is_file():
            return candidate
    fail(f"No CapCut draft JSON found in empty template: {project_dir}")


def verify_empty_template(template_dir: Path) -> Path:
    draft_file = find_draft_file(template_dir)
    try:
        draft = json.loads(draft_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Could not read template draft JSON: {error}")

    duration = draft.get("duration", 0) or 0
    tracks = draft.get("tracks", []) or []
    if not isinstance(duration, (int, float)) or duration != 0:
        fail(f"Template is not empty: duration={duration}")
    if not isinstance(tracks, list) or tracks:
        count = len(tracks) if isinstance(tracks, list) else "invalid"
        fail(f"Template is not empty: track_count={count}")
    return draft_file


def capcut_is_open() -> tuple[bool | None, str]:
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["osascript", "-e", 'application "CapCut" is running'],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None, "osascript-unavailable"
        value = result.stdout.strip().lower()
        if value not in {"true", "false"}:
            return None, "osascript-unavailable"
        return value == "true", "osascript"

    try:
        result = subprocess.run(
            ["pgrep", "-x", "CapCut"], check=False, capture_output=True, text=True
        )
    except FileNotFoundError:
        return None, "pgrep-unavailable"
    return result.returncode == 0, "pgrep"


def draft_fingerprint(draft_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(draft_dir.rglob("*.json")):
        digest.update(str(path.relative_to(draft_dir)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def resolve_template(raw: str, drafts_root: Path) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = drafts_root / candidate
    template = candidate.resolve()
    try:
        template.relative_to(drafts_root)
    except ValueError:
        fail("Empty template must live inside the resolved CapCut drafts root")
    if not template.is_dir():
        fail(f"Empty template directory does not exist: {template}")
    return template


def run() -> dict:
    args = parse_args()
    project_dir = args.project_dir.expanduser().resolve()
    project_name = project_dir.name
    if not PROJECT_NAME_RE.fullmatch(project_name):
        fail(f"Project name is not canonical YYYY-MM-DD_video-slug: {project_name}")
    if not project_dir.is_dir():
        fail(f"Canonical video project directory does not exist: {project_dir}")

    drafts_root = args.drafts_root.expanduser().resolve()
    if not drafts_root.is_dir():
        fail(f"CapCut drafts root does not exist: {drafts_root}")

    template_dir = resolve_template(args.empty_template, drafts_root)
    template_draft_file = verify_empty_template(template_dir)
    source_fingerprint = draft_fingerprint(template_dir)
    target_dir = drafts_root / project_name
    receipt_file = project_dir / "editor-projects" / "capcut-draft.json"
    if target_dir.exists():
        fail(f"Target CapCut draft already exists; nothing was changed: {target_dir}")
    if receipt_file.exists():
        fail(f"CapCut draft receipt already exists; nothing was changed: {receipt_file}")

    capcutbot_cli = args.capcutbot_dir.expanduser().resolve() / "src" / "cli.js"
    if not capcutbot_cli.is_file():
        fail(f"CapCutBot CLI not found: {capcutbot_cli}")

    is_open, process_check = capcut_is_open()
    command = [
        "node",
        str(capcutbot_cli),
        "duplicate",
        str(template_dir),
        str(target_dir),
    ]
    if args.dry_run:
        command.append("--dry-run")

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        fail(result.stderr.strip() or "CapCutBot duplicate command failed")
    try:
        capcutbot_result = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        fail(f"CapCutBot returned invalid JSON: {error}")

    created_draft_file = None
    target_fingerprint = None
    if args.apply:
        if not target_dir.is_dir():
            fail("CapCutBot reported success but did not create the target draft")
        created_draft_file = verify_empty_template(target_dir)
        target_fingerprint = draft_fingerprint(target_dir)

    output = {
        "mode": "dry-run" if args.dry_run else "apply",
        "project_name": project_name,
        "project_dir": str(project_dir),
        "drafts_root": str(drafts_root),
        "empty_template_dir": str(template_dir),
        "empty_template_draft_file": str(template_draft_file),
        "target_draft_dir": str(target_dir),
        "created_draft_file": str(created_draft_file) if created_draft_file else None,
        "receipt_file": str(receipt_file),
        "capcut_open": is_open,
        "process_check": process_check,
        "warnings": ([
            "CapCut is open; refresh the project list or restart CapCut if the new draft does not appear."
        ] if is_open else []),
        "source_fingerprint": source_fingerprint,
        "target_fingerprint": target_fingerprint,
        "source_modified": False,
        "target_overwritten": False,
        "backup_file": None,
        "capcutbot": capcutbot_result,
    }

    if args.apply:
        receipt_file.parent.mkdir(parents=True, exist_ok=True)
        receipt = {
            **output,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "empty-named-draft-created",
            "timeline_editing_completed": False,
        }
        temporary = receipt_file.with_suffix(".json.tmp")
        temporary.write_text(f"{json.dumps(receipt, indent=2)}\n", encoding="utf-8")
        temporary.replace(receipt_file)
        output["receipt_written"] = True
    else:
        output["receipt_written"] = False

    return output


if __name__ == "__main__":
    try:
        print(json.dumps(run(), indent=2))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
