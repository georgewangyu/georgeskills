#!/usr/bin/env python3
"""
Record document-access events into memory/doc_access_index.json and doc_access_log.jsonl.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from access_index import record_doc_access
from repo_paths import resolve_private_repo_root


PRIVATE_REPO_ROOT = resolve_private_repo_root()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record doc access for one or more markdown files.")
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Path to a document. Repeatable. Relative paths are resolved from private repo root.",
    )
    parser.add_argument(
        "--source",
        default="manual",
        help="Access source label (default: manual).",
    )
    parser.add_argument(
        "--at",
        help="Optional UTC timestamp override (ISO-8601).",
    )
    return parser.parse_args()


def resolve_input_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = (PRIVATE_REPO_ROOT / path).resolve()
    return path


def main() -> int:
    args = parse_args()
    if not args.paths:
        raise SystemExit("Provide at least one --path.")

    touched = 0
    for raw in args.paths:
        path = resolve_input_path(raw)
        if not path.exists() or not path.is_file():
            print(f"missing: {raw}")
            continue
        if not path.suffix.lower() == ".md":
            print(f"skip (not markdown): {path.relative_to(PRIVATE_REPO_ROOT)}")
            continue
        record_doc_access(
            private_repo_root=PRIVATE_REPO_ROOT,
            source_path=path,
            access_source=args.source,
            accessed_at=args.at,
        )
        touched += 1
        print(f"logged: {path.relative_to(PRIVATE_REPO_ROOT)}")

    return 0 if touched else 1


if __name__ == "__main__":
    raise SystemExit(main())
