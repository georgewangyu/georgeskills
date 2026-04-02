#!/usr/bin/env python3
"""
Query canonical and candidate memory records with simple filters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
MEMORY_DIR = PRIVATE_REPO_ROOT / "memory"
CANDIDATES_DIR = MEMORY_DIR / "candidates"

CANONICAL_FILES = [
    MEMORY_DIR / "decisions.jsonl",
    MEMORY_DIR / "commitments.jsonl",
    MEMORY_DIR / "status_changes.jsonl",
    MEMORY_DIR / "people.jsonl",
    MEMORY_DIR / "patterns.jsonl",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query memory records.")
    parser.add_argument("--type", dest="record_type")
    parser.add_argument("--status")
    parser.add_argument("--durability")
    parser.add_argument("--entity", action="append", default=[])
    parser.add_argument("--text", help="Substring match against title, summary, tags, and source_ref.")
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--source", help="Substring match against source_ref.")
    parser.add_argument("--canonical-only", action="store_true")
    parser.add_argument("--candidates-only", action="store_true")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args()


def iter_jsonl(path: Path) -> Iterable[dict[str, object]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                yield value


def all_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    if not args.candidates_only:
        paths.extend([path for path in CANONICAL_FILES if path.exists()])
    if not args.canonical_only and CANDIDATES_DIR.exists():
        paths.extend(sorted(CANDIDATES_DIR.glob("*.jsonl")))
    return paths


def matches(args: argparse.Namespace, record: dict[str, object]) -> bool:
    if args.record_type and record.get("type") != args.record_type:
        return False
    if args.status and record.get("status") != args.status:
        return False
    if args.durability and record.get("durability") != args.durability:
        return False

    date_text = str(record.get("date", ""))
    if args.from_date and date_text and date_text < args.from_date:
        return False
    if args.to_date and date_text and date_text > args.to_date:
        return False

    entities = [str(entity).lower() for entity in record.get("entities", [])]
    for wanted in args.entity:
        if wanted.lower() not in entities:
            return False

    source_ref = str(record.get("source_ref", ""))
    if args.source and args.source.lower() not in source_ref.lower():
        return False

    if args.text:
        haystack = " ".join(
            [
                str(record.get("title", "")),
                str(record.get("summary", "")),
                " ".join(str(tag) for tag in record.get("tags", [])),
                source_ref,
            ]
        ).lower()
        if args.text.lower() not in haystack:
            return False

    return True


def main() -> int:
    args = parse_args()
    paths = all_paths(args)
    results: list[dict[str, object]] = []
    for path in paths:
        for record in iter_jsonl(path):
            if matches(args, record):
                enriched = dict(record)
                enriched["_store"] = path.relative_to(PRIVATE_REPO_ROOT).as_posix()
                results.append(enriched)

    results.sort(key=lambda item: (str(item.get("date", "")), str(item.get("id", ""))), reverse=True)
    limited = results[: args.limit]

    if args.json_output:
        for record in limited:
            print(json.dumps(record, ensure_ascii=False))
        return 0

    for record in limited:
        print(f"{record.get('date', '?')} [{record.get('type', '?')}/{record.get('status', '?')}] {record.get('title', '')}")
        print(f"  summary: {record.get('summary', '')}")
        print(f"  source:  {record.get('source_ref', '')}")
        print(f"  store:   {record.get('_store', '')}")
        print(f"  tags:    {', '.join(str(tag) for tag in record.get('tags', []))}")
        print()

    print(f"{len(limited)} result(s) shown")
    if len(results) > len(limited):
        print(f"{len(results) - len(limited)} more omitted by --limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
