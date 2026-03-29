#!/usr/bin/env python3
"""
Promote reviewed candidate memories into canonical stores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
MEMORY_DIR = PRIVATE_REPO_ROOT / "memory"
CANDIDATES_DIR = MEMORY_DIR / "candidates"

TARGET_FILES = {
    "decision": MEMORY_DIR / "decisions.jsonl",
    "commitment": MEMORY_DIR / "commitments.jsonl",
    "status_change": MEMORY_DIR / "status_changes.jsonl",
    "person": MEMORY_DIR / "people.jsonl",
    "pattern": MEMORY_DIR / "patterns.jsonl",
}

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


def candidate_path_for_date(date_text: str) -> Path:
    return CANDIDATES_DIR / f"{date_text}.jsonl"


def load_jsonl(path: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                items.append(value)
    return items


def existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {str(item.get("id")) for item in load_jsonl(path) if item.get("id")}


def append_jsonl(path: Path, items: list[dict[str, object]]) -> None:
    if not items:
        return
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote candidate memories into canonical stores.")
    parser.add_argument("--date", help="Candidate date in YYYY-MM-DD format.")
    parser.add_argument("--path", help="Direct candidate JSONL path.")
    parser.add_argument("--id", action="append", dest="ids", help="Candidate id to promote. Repeatable.")
    parser.add_argument("--all", action="store_true", help="Promote all candidates in the file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate_path = Path(args.path) if args.path else candidate_path_for_date(args.date or "")
    if not candidate_path.exists():
        raise SystemExit(f"Candidate file not found: {candidate_path}")
    if not args.all and not args.ids:
        raise SystemExit("Provide --all or at least one --id.")

    candidates = load_jsonl(candidate_path)
    selected: list[dict[str, object]] = []
    requested_ids = set(args.ids or [])

    for candidate in candidates:
        candidate_id = str(candidate.get("id", ""))
        if args.all or candidate_id in requested_ids:
            missing = REQUIRED_FIELDS - set(candidate.keys())
            if missing:
                raise SystemExit(f"{candidate_id or '<unknown>'} missing fields: {sorted(missing)}")
            promoted = dict(candidate)
            promoted["status"] = "accepted"
            selected.append(promoted)

    if not selected:
        raise SystemExit("No matching candidates found.")

    grouped: dict[Path, list[dict[str, object]]] = {}
    for record in selected:
        record_type = str(record.get("type", ""))
        target = TARGET_FILES.get(record_type)
        if target is None:
            raise SystemExit(f"Unsupported record type: {record_type}")
        grouped.setdefault(target, []).append(record)

    promoted_count = 0
    for target_path, items in grouped.items():
        seen = existing_ids(target_path)
        new_items = [item for item in items if str(item.get("id")) not in seen]
        append_jsonl(target_path, new_items)
        promoted_count += len(new_items)
        print(f"{target_path.relative_to(PRIVATE_REPO_ROOT)} <- {len(new_items)}")

    return 0 if promoted_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
