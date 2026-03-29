#!/usr/bin/env python3
"""
Validate canonical and candidate memory JSONL files.
"""

from __future__ import annotations

import json
from pathlib import Path

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
MEMORY_DIR = PRIVATE_REPO_ROOT / "memory"

REQUIRED_FIELDS = {
    "id",
    "type",
    "title",
    "summary",
    "date",
    "valid_from",
    "status",
    "durability",
    "strength",
    "last_reinforced_on",
    "source_ref",
    "tags",
    "supersedes",
}

ALLOWED_TYPES = {"decision", "commitment", "status_change", "person", "pattern"}
ALLOWED_STATUS = {"candidate", "accepted", "stale", "superseded"}
ALLOWED_DURABILITY = {"ephemeral", "active", "durable"}


def iter_jsonl_files() -> list[Path]:
    canonical = [
        MEMORY_DIR / "decisions.jsonl",
        MEMORY_DIR / "commitments.jsonl",
        MEMORY_DIR / "status_changes.jsonl",
        MEMORY_DIR / "people.jsonl",
        MEMORY_DIR / "patterns.jsonl",
    ]
    paths = [path for path in canonical if path.exists()]
    paths.extend(sorted((MEMORY_DIR / "candidates").glob("*.jsonl")))
    return paths


def main() -> int:
    errors: list[str] = []

    for path in iter_jsonl_files():
        with path.open(encoding="utf-8") as handle:
            for index, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path}:{index}: invalid JSON: {exc}")
                    continue
                if not isinstance(value, dict):
                    errors.append(f"{path}:{index}: record is not an object")
                    continue
                missing = REQUIRED_FIELDS - set(value.keys())
                if missing:
                    errors.append(f"{path}:{index}: missing fields {sorted(missing)}")
                record_type = value.get("type")
                if record_type not in ALLOWED_TYPES:
                    errors.append(f"{path}:{index}: invalid type {record_type!r}")
                status = value.get("status")
                if status not in ALLOWED_STATUS:
                    errors.append(f"{path}:{index}: invalid status {status!r}")
                durability = value.get("durability")
                if durability not in ALLOWED_DURABILITY:
                    errors.append(f"{path}:{index}: invalid durability {durability!r}")

    if errors:
        for error in errors:
            print(error)
        return 1

    for path in iter_jsonl_files():
        print(f"{path.relative_to(PRIVATE_REPO_ROOT)} ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
