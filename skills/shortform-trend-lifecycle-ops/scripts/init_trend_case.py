#!/usr/bin/env python3
"""Create a non-destructive short-form trend lifecycle case folder."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INDEX_HEADER = """# Short-Form Trend Lifecycle Cases

| Trend case | Discovered | Current stage | Usable window | Confidence |
| --- | --- | --- | --- | --- |
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--discovered-on", required=True)
    return parser.parse_args()


def validate_date(value: str) -> str:
    dt.date.fromisoformat(value)
    return value


def main() -> int:
    args = parse_args()
    discovered_on = validate_date(args.discovered_on)
    if not SLUG_RE.fullmatch(args.slug):
        raise SystemExit("--slug must be lowercase kebab-case")
    title = args.title.strip()
    if not title:
        raise SystemExit("--title must be a non-empty string")
    if "\n" in title or "\r" in title:
        raise SystemExit("--title must be a single-line string")

    trend_id = f"{discovered_on}_{args.slug}"
    root = args.root.expanduser().resolve()
    case_dir = root / trend_id
    if case_dir.exists():
        raise SystemExit(f"refusing to overwrite existing case: {case_dir}")

    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "INDEX.md"
    if index_path.is_symlink():
        raise SystemExit(f"refusing symlinked case index: {index_path}")
    if not index_path.exists():
        index_path.write_text(INDEX_HEADER, encoding="utf-8")

    case_dir.mkdir()
    observed_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    case_md = f'''---
trend_case_schema: "shortform-trend-lifecycle-v1"
trend_id: "{trend_id}"
title: "{title.replace('"', "'")}"
discovered_on: "{discovered_on}"
snapshot_at: "{observed_at}"
platforms: "unknown"
earliest_source_backed_at: null
first_breakout_at: null
copy_wave_onset_at: null
peak_at: null
decay_onset_at: null
current_stage: "unknown"
usable_window: "unknown"
confidence: "low"
---

# {title}

## Decision

Research incomplete.

## Format Grammar

### Included

### Excluded

### Parent family and mutation boundary

## Lifecycle Card

| Milestone | Finding | Confidence |
| --- | --- | --- |
| Onset | Unknown | Low |
| First breakout | Unknown | Low |
| Copy-wave onset | Unknown | Low |
| Peak | Unknown | Low |
| Decay onset | Unknown | Low |
| Current stage | Unknown | Low |

## Observed Evidence

## Source and Credit Lineage

## Replication and Velocity

## Remaining Usable Window

## Adaptation Boundary

## Inference

## Confidence and Gaps

## Collection Receipt

'''
    (case_dir / "case.md").write_text(case_md, encoding="utf-8")
    (case_dir / "evidence.jsonl").write_text("", encoding="utf-8")

    row = f'| [{title}]({trend_id}/case.md) | `{discovered_on}` | `unknown` | `unknown` | `low` |\n'
    existing = index_path.read_text(encoding="utf-8")
    if f"({trend_id}/case.md)" not in existing:
        separator = "" if existing.endswith("\n") else "\n"
        index_path.write_text(existing + separator + row, encoding="utf-8")

    print(case_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
