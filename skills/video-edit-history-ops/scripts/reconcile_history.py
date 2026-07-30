#!/usr/bin/env python3
"""Audit reviewable video projects against a private edit-history index.

The command is intentionally read-only. It reports missing or broken receipts
so an agent can backfill them from inspectable evidence without guessing from
filenames.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


POINTER_NAME = "AI_EDIT_HISTORY.md"
DISCOVERY_MARKERS = ("AI_EDIT_HISTORY.md", "REEL_BRIEF.md", "VIDEO_EDIT_GATES.md")
REVIEWABLE_BRIEF_SIGNALS = (
    "ready for creator review",
    "review render:",
    "reviewed render:",
    "creator-selected",
    "creator selected",
    "final export:",
    "published",
)
REVIEWABLE_GATE_SIGNALS = (
    "rendered evaluation: passed",
    "rendered evaluation `passed`",
    "final acceptance: passed",
    "final acceptance `passed`",
    "review export:",
)
REVIEW_EVIDENCE_NAMES = {
    "FINAL_ACCEPTANCE.md",
    "FINAL_ACCEPTANCE_REPORT.md",
    "QA_REPORT.md",
    "VISUAL_COVERAGE_QA.md",
}
RENDER_DIR_NAMES = {
    "exports",
    "outputs",
    "proxy",
    "renders",
    "review",
    "working",
}
SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "raw",
}
VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v"}


@dataclass(frozen=True)
class Issue:
    code: str
    project: Path
    detail: str


def parse_frontmatter(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            result[match.group(1)] = match.group(2).strip().strip("\"'")
    return result


def markdown_link_paths(index_path: Path, text: str) -> set[Path]:
    """Return resolved local paths from Markdown links in an index."""
    paths: set[Path] = set()
    destinations = re.findall(
        r"\]\(\s*(?:<([^>]+)>|([^\s)]+))",
        text,
    )
    for angled, plain in destinations:
        destination = angled or plain
        parsed = urlsplit(destination)
        if parsed.scheme or parsed.netloc:
            continue
        local_path = Path(unquote(parsed.path))
        if not local_path.is_absolute():
            local_path = index_path.parent / local_path
        paths.add(local_path.resolve())
    return paths


def contains_signal(path: Path, signals: tuple[str, ...]) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    return any(signal in text for signal in signals)


def is_reviewable(project: Path) -> bool:
    if (project / POINTER_NAME).is_file():
        return True
    if contains_signal(project / "REEL_BRIEF.md", REVIEWABLE_BRIEF_SIGNALS):
        return True
    if contains_signal(
        project / "VIDEO_EDIT_GATES.md", REVIEWABLE_GATE_SIGNALS
    ):
        return True

    for current, directories, filenames in os.walk(project):
        directories[:] = [
            name for name in directories if name not in SKIP_DIR_NAMES
        ]
        current_path = Path(current)
        relative_parts = {
            part.lower()
            for part in current_path.relative_to(project).parts
        }
        for filename in filenames:
            if filename in REVIEW_EVIDENCE_NAMES:
                return True
            suffix = Path(filename).suffix.lower()
            if (
                suffix in VIDEO_SUFFIXES
                and relative_parts.intersection(RENDER_DIR_NAMES)
            ):
                return True
    return False


def looks_like_project(path: Path) -> bool:
    if any((path / marker).is_file() for marker in DISCOVERY_MARKERS):
        return True
    if any(
        (path / marker).is_file()
        for marker in ("INTAKE.md", "PROJECT_STATUS.json")
    ):
        return True
    return any(
        child.is_dir() and child.name.lower() in RENDER_DIR_NAMES
        for child in path.iterdir()
    )


def discover_projects(roots: list[Path]) -> list[Path]:
    projects: set[Path] = set()
    for supplied in roots:
        root = supplied.expanduser().resolve()
        if not root.is_dir():
            continue
        if looks_like_project(root):
            if is_reviewable(root):
                projects.add(root)
        else:
            for child in root.iterdir():
                if (
                    child.is_dir()
                    and not child.name.startswith("_")
                    and looks_like_project(child)
                    and is_reviewable(child)
                ):
                    projects.add(child.resolve())
    return sorted(projects)


def resolve_record(history_root: Path, value: str) -> Path | None:
    """Resolve a root-relative history record without allowing path escape."""
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return None
    record = (history_root / candidate).resolve()
    history_dir = (history_root / "history").resolve()
    if not record.is_relative_to(history_dir):
        return None
    return record


def audit_project(
    history_root: Path, index_links: set[Path], project: Path
) -> list[Issue]:
    pointer = project / POINTER_NAME
    if not pointer.is_file():
        return [
            Issue(
                "MISSING_POINTER",
                project,
                f"reviewable project has no {POINTER_NAME}",
            )
        ]
    try:
        resolved_pointer = pointer.resolve()
        resolved_pointer.relative_to(project.resolve())
    except (OSError, RuntimeError, ValueError):
        return [
            Issue(
                "INVALID_POINTER",
                project,
                f"{POINTER_NAME} resolves outside the project or cannot "
                "be resolved safely",
            )
        ]

    fields = parse_frontmatter(resolved_pointer)
    issues: list[Issue] = []
    for required in (
        "schema",
        "video_id",
        "history_record",
        "capture_stage",
        "captured_at",
    ):
        if not fields.get(required):
            issues.append(
                Issue(
                    "INVALID_POINTER",
                    project,
                    f"{POINTER_NAME} is missing frontmatter field {required}",
                )
            )
    if fields.get("schema") and fields["schema"] != "ai-edit-history-pointer-v1":
        issues.append(
            Issue(
                "INVALID_POINTER",
                project,
                f"unexpected pointer schema {fields['schema']}",
            )
        )
    if issues:
        return issues

    record = resolve_record(history_root, fields["history_record"])
    if record is None:
        return [
            Issue(
                "INVALID_POINTER",
                project,
                "history_record must be a history-root-relative path "
                "beneath history/",
            )
        ]
    if not record.is_file():
        return [
            Issue(
                "MISSING_RECORD",
                project,
                f"pointer target does not exist: {record}",
            )
        ]

    record_fields = parse_frontmatter(record)
    if record_fields.get("video_id") != fields["video_id"]:
        issues.append(
            Issue(
                "VIDEO_ID_MISMATCH",
                project,
                "pointer video_id "
                f"{fields['video_id']} != record video_id "
                f"{record_fields.get('video_id', '<missing>')}",
            )
        )

    index_target = record.relative_to(
        (history_root / "history").resolve()
    ).as_posix()
    if record not in index_links:
        issues.append(
            Issue(
                "MISSING_INDEX_LINK",
                project,
                f"history/INDEX.md does not link {index_target}",
            )
        )
    return issues


def audit_history_records(
    history_root: Path, index_links: set[Path]
) -> list[Issue]:
    issues: list[Issue] = []
    history_dir = (history_root / "history").resolve()
    for record in sorted(history_dir.glob("*/*.md")):
        target = record.relative_to(history_dir).as_posix()
        try:
            resolved_record = record.resolve()
            resolved_record.relative_to(history_dir)
        except (OSError, RuntimeError, ValueError):
            issues.append(
                Issue(
                    "INVALID_RECORD",
                    history_root,
                    f"detailed record resolves outside history/ or cannot "
                    f"be resolved safely: {target}",
                )
            )
            continue
        if resolved_record not in index_links:
            issues.append(
                Issue(
                    "ORPHAN_RECORD",
                    history_root,
                    f"detailed record is missing from index: {target}",
                )
            )
    return issues


def run_audit(history_root: Path, project_roots: list[Path]) -> tuple[list[Path], list[Issue]]:
    history_root = history_root.expanduser().resolve()
    try:
        history_dir = (history_root / "history").resolve()
        history_dir.relative_to(history_root)
    except (OSError, RuntimeError, ValueError):
        return [], [
            Issue(
                "INVALID_HISTORY_ROOT",
                history_root,
                "history/ resolves outside the supplied history root or "
                "cannot be resolved safely",
            )
        ]
    unresolved_index = history_dir / "INDEX.md"
    if not unresolved_index.is_file():
        return [], [
            Issue(
                "MISSING_INDEX",
                history_root,
                f"history index does not exist: {unresolved_index}",
            )
        ]
    try:
        index_path = unresolved_index.resolve()
        index_path.relative_to(history_dir)
    except (OSError, RuntimeError, ValueError):
        return [], [
            Issue(
                "INVALID_INDEX",
                history_root,
                "history/INDEX.md resolves outside history/ or cannot be "
                "resolved safely",
            )
        ]
    index_text = index_path.read_text(encoding="utf-8", errors="replace")
    index_links = markdown_link_paths(index_path, index_text)
    projects = discover_projects(project_roots)
    issues = audit_history_records(history_root, index_links)
    for project in projects:
        issues.extend(audit_project(history_root, index_links, project))
    return projects, issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("history_root", type=Path)
    parser.add_argument("project_roots", nargs="+", type=Path)
    args = parser.parse_args()

    projects, issues = run_audit(args.history_root, args.project_roots)
    for issue in issues:
        print(f"{issue.code}: {issue.project}: {issue.detail}")
    if issues:
        print(
            f"HOLD: audited {len(projects)} reviewable project(s); "
            f"{len(issues)} issue(s)"
        )
        return 1
    print(
        f"OK: audited {len(projects)} reviewable project(s); "
        "all history pointers, records, and index links agree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
