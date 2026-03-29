#!/usr/bin/env python3
"""
Extract conservative structured-memory candidates from daily summaries.

Writes per-day candidate JSONL files to `<private-repo>/memory/candidates/`.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
JOURNAL_SUMMARIES_DIR = PRIVATE_REPO_ROOT / "journal" / "summaries"
MEMORY_DIR = PRIVATE_REPO_ROOT / "memory"
CANDIDATES_DIR = MEMORY_DIR / "candidates"


@dataclass
class Section:
    level: int
    title: str
    anchor: str
    parent_titles: list[str]
    lines: list[str]


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def summary_path_for_date(date_text: str) -> Path:
    parts = date_text.split("-")
    if len(parts) != 3:
        raise ValueError(f"Invalid date: {date_text}")
    year, month, _ = parts
    return JOURNAL_SUMMARIES_DIR / year / month / f"{date_text}_Summary.md"


def markdown_anchor(title: str) -> str:
    slug = slugify(title.replace("/", " "))
    return slug or "section"


def parse_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    heading_stack: list[tuple[int, str]] = []
    current: Section | None = None

    for raw_line in text.splitlines():
        heading_match = re.match(r"^(#{2,6})\s+(.*)$", raw_line)
        if heading_match:
            if current is not None:
                sections.append(current)
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            parent_titles = [title_text for _, title_text in heading_stack]
            current = Section(
                level=level,
                title=title,
                anchor=markdown_anchor(title),
                parent_titles=parent_titles,
                lines=[],
            )
            heading_stack.append((level, title))
            continue

        if current is not None:
            current.lines.append(raw_line)

    if current is not None:
        sections.append(current)
    return sections


def bullet_lines(section: Section) -> list[str]:
    bullets: list[str] = []
    for raw_line in section.lines:
        stripped = raw_line.strip()
        match = re.match(r"^[-*]\s+(.*)$", stripped)
        if match:
            text = match.group(1).strip()
            if text:
                bullets.append(text)
    return bullets


def clean_summary_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text.rstrip(".")


def infer_durability(memory_type: str, section: Section) -> str:
    if memory_type == "decision":
        return "durable"
    if memory_type in {"commitment", "status_change"}:
        return "active"
    if memory_type == "pattern" and section.title == "Narrator Notes":
        return "durable"
    return "active"


def infer_strength(memory_type: str, section: Section) -> int:
    if memory_type in {"decision", "commitment", "status_change"}:
        return 3
    if memory_type == "pattern" and section.title == "Narrator Notes":
        return 3
    return 2


def memory_title(memory_type: str, text: str, section: Section, index: int) -> str:
    trimmed = clean_summary_text(text)
    if len(trimmed) <= 90:
        return trimmed
    prefix = {
        "decision": "Decision",
        "commitment": "Commitment",
        "status_change": section.title,
        "pattern": section.title,
    }.get(memory_type, section.title)
    return f"{prefix} {index}"


def build_record(
    *,
    date_text: str,
    section: Section,
    memory_type: str,
    text: str,
    index: int,
    source_path: Path,
) -> dict[str, object]:
    title = memory_title(memory_type, text, section, index)
    anchor = section.anchor
    id_parts = [memory_type, slugify(section.title), date_text, str(index)]
    return {
        "id": "_".join(part for part in id_parts if part),
        "type": memory_type,
        "title": title,
        "summary": clean_summary_text(text),
        "entities": [],
        "date": date_text,
        "valid_from": date_text,
        "valid_to": None,
        "status": "candidate",
        "durability": infer_durability(memory_type, section),
        "strength": infer_strength(memory_type, section),
        "last_reinforced_on": date_text,
        "source_ref": f"{source_path.relative_to(PRIVATE_REPO_ROOT).as_posix()}#{anchor}",
        "tags": [slugify(memory_type), slugify(section.title)],
        "supersedes": [],
    }


def candidate_records_for_summary(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})_Summary\.md$", path.name)
    if not date_match:
        raise ValueError(f"Could not infer date from {path}")
    date_text = date_match.group(1)

    sections = parse_sections(text)
    records: list[dict[str, object]] = []

    for section in sections:
        bullets = bullet_lines(section)
        if section.title == "Key Decisions":
            for index, bullet in enumerate(bullets, start=1):
                records.append(
                    build_record(
                        date_text=date_text,
                        section=section,
                        memory_type="decision",
                        text=bullet,
                        index=index,
                        source_path=path,
                    )
                )
        elif section.title == "Tomorrow":
            for index, bullet in enumerate(bullets, start=1):
                records.append(
                    build_record(
                        date_text=date_text,
                        section=section,
                        memory_type="commitment",
                        text=bullet,
                        index=index,
                        source_path=path,
                    )
                )
        elif section.parent_titles and section.parent_titles[-1].startswith("Conversation Milestones"):
            for index, bullet in enumerate(bullets, start=1):
                records.append(
                    build_record(
                        date_text=date_text,
                        section=section,
                        memory_type="status_change",
                        text=bullet,
                        index=index,
                        source_path=path,
                    )
                )
        elif section.title in {"Challenges", "Narrator Notes"}:
            for index, bullet in enumerate(bullets, start=1):
                records.append(
                    build_record(
                        date_text=date_text,
                        section=section,
                        memory_type="pattern",
                        text=bullet,
                        index=index,
                        source_path=path,
                    )
                )

    return records


def write_candidates(path: Path, records: Iterable[dict[str, object]]) -> Path:
    ensure_dir(CANDIDATES_DIR)
    target_path = CANDIDATES_DIR / f"{path.stem.replace('_Summary', '')}.jsonl"
    with target_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target_path


def find_summary_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    if args.date:
        paths.append(summary_path_for_date(args.date))
    if args.path:
        paths.append(Path(args.path))
    if args.all_month:
        month_dir = JOURNAL_SUMMARIES_DIR / args.all_month[:4] / args.all_month[5:7]
        paths.extend(sorted(month_dir.glob(f"{args.all_month}-*_Summary.md")))
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(path)
    return deduped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract structured-memory candidates from daily summaries.")
    parser.add_argument("--date", help="Target summary date in YYYY-MM-DD format.")
    parser.add_argument("--path", help="Direct path to a summary markdown file.")
    parser.add_argument("--all-month", help="Extract all summaries for a month in YYYY-MM format.")
    parser.add_argument("--print", action="store_true", dest="print_records", help="Print candidate JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary_paths = find_summary_paths(args)
    if not summary_paths:
        raise SystemExit("Provide --date, --path, or --all-month.")

    wrote_any = False
    for summary_path in summary_paths:
        if not summary_path.exists():
            print(f"missing: {summary_path}")
            continue
        records = candidate_records_for_summary(summary_path)
        out_path = write_candidates(summary_path, records)
        wrote_any = True
        print(
            f"{summary_path.relative_to(PRIVATE_REPO_ROOT)} -> "
            f"{out_path.relative_to(PRIVATE_REPO_ROOT)} ({len(records)} candidates)"
        )
        if args.print_records:
            for record in records:
                print(json.dumps(record, ensure_ascii=False))
    return 0 if wrote_any else 1


if __name__ == "__main__":
    raise SystemExit(main())
