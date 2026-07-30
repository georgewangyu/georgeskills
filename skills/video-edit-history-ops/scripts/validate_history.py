#!/usr/bin/env python3
"""Validate a video-edit-history repository using only the standard library."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED_ROOT_FILES = (
    "history/INDEX.md",
    "registries/EDITING_DEFAULTS.md",
    "registries/FAILURE_MODES.md",
    "templates/VIDEO_HISTORY_ENTRY.md",
)
REQUIRED_FIELDS = (
    "schema",
    "video_id",
    "title",
    "reviewed_at",
    "status",
    "lesson_status",
    "tags",
)
REQUIRED_HEADINGS = (
    "Evidence",
    "Failure Analysis",
    "Reusable Lessons",
    "Next Iteration",
)
EXPECTED_SCHEMA = "video-edit-history-v1"


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            result[match.group(1)] = match.group(2).strip()
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("history_root", type=Path)
    args = parser.parse_args()
    root = args.history_root.resolve()
    errors: list[str] = []
    try:
        history_dir = (root / "history").resolve()
        history_dir.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        print(
            "ERROR: history/ resolves outside the supplied history root or "
            "cannot be resolved safely"
        )
        return 1

    for relative in REQUIRED_ROOT_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    records = sorted(history_dir.glob("*/*.md")) if history_dir.exists() else []
    unresolved_index = history_dir / "INDEX.md"
    try:
        index_path = unresolved_index.resolve()
        index_path.relative_to(history_dir)
        index_is_safe = True
    except (OSError, RuntimeError, ValueError):
        index_path = unresolved_index
        index_is_safe = False
        errors.append(
            "history/INDEX.md resolves outside history/ or cannot be "
            "resolved safely"
        )
    index_text = (
        index_path.read_text(encoding="utf-8")
        if index_is_safe and index_path.is_file()
        else ""
    )
    index_links = markdown_link_paths(index_path, index_text)
    seen_ids: dict[str, Path] = {}
    history_dir_resolved = history_dir
    for path in records:
        try:
            resolved_path = path.resolve()
            resolved_path.relative_to(history_dir_resolved)
        except (OSError, RuntimeError, ValueError):
            errors.append(
                f"{path.relative_to(root)}: detailed record resolves outside "
                "history/ or cannot be resolved safely"
            )
            continue
        text = path.read_text(encoding="utf-8")
        fields = frontmatter(text)
        for field in REQUIRED_FIELDS:
            if not fields.get(field):
                errors.append(
                    f"{path.relative_to(root)}: missing frontmatter field {field}"
                )
        schema = fields.get("schema")
        if schema and schema != EXPECTED_SCHEMA:
            errors.append(
                f"{path.relative_to(root)}: unexpected schema {schema}; "
                f"expected {EXPECTED_SCHEMA}"
            )
        video_id = fields.get("video_id")
        if video_id:
            if video_id in seen_ids:
                prior = seen_ids[video_id].relative_to(root)
                errors.append(
                    f"{path.relative_to(root)}: duplicate video_id "
                    f"{video_id} (also in {prior})"
                )
            seen_ids[video_id] = path
        headings = set(re.findall(r"^## (.+)$", text, flags=re.MULTILINE))
        for heading in REQUIRED_HEADINGS:
            if heading not in headings:
                errors.append(
                    f"{path.relative_to(root)}: missing section {heading}"
                )
        has_feedback = any(
            heading == "Creator Feedback"
            or heading.endswith("'s Explicit Feedback")
            for heading in headings
        )
        if not has_feedback:
            errors.append(
                f"{path.relative_to(root)}: missing creator feedback section"
            )
        if resolved_path not in index_links:
            errors.append(
                f"{path.relative_to(root)}: missing link from history/INDEX.md"
            )

    if index_text:
        for resolved in index_links:
            try:
                relative = resolved.relative_to(history_dir_resolved)
            except ValueError:
                continue
            if (
                relative.parts
                and relative.parts[0].startswith("20")
                and resolved.suffix == ".md"
                and not resolved.is_file()
            ):
                errors.append(
                    "history/INDEX.md: broken detailed-record link "
                    f"{relative.as_posix()}"
                )

    if not records:
        errors.append("no detailed history records found under history/YYYY/")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        f"OK: {len(records)} history records; "
        f"{len(seen_ids)} unique video ids"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
