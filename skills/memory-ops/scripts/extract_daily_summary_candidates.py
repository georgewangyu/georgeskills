#!/usr/bin/env python3
"""
Extract conservative structured-memory candidates.

Writes per-day candidate JSONL files to `<private-repo>/memory/candidates/`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from access_index import record_doc_access
from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
JOURNAL_SUMMARIES_DIR = PRIVATE_REPO_ROOT / "journal" / "summaries"
MEMORY_DIR = PRIVATE_REPO_ROOT / "memory"
CANDIDATES_DIR = MEMORY_DIR / "candidates"
SUMMARY_FILENAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_Summary\.md$")


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


def date_from_summary_path(path: Path) -> str:
    match = SUMMARY_FILENAME_RE.search(path.name)
    if not match:
        raise ValueError(f"Could not infer date from {path}")
    return match.group(1)


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


def record_source_access(path: Path, *, access_source: str) -> None:
    record_doc_access(
        private_repo_root=PRIVATE_REPO_ROOT,
        source_path=path,
        access_source=access_source,
    )


def build_record(
    *,
    date_text: str,
    section: Section,
    memory_type: str,
    text: str,
    index: int,
    source_path: Path,
    id_parts: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, object]:
    title = memory_title(memory_type, text, section, index)
    anchor = section.anchor
    final_id_parts = id_parts or [memory_type, slugify(section.title), date_text, str(index)]
    final_tags = tags or [slugify(memory_type), slugify(section.title)]
    return {
        "id": "_".join(part for part in final_id_parts if part),
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
        "tags": final_tags,
        "supersedes": [],
    }


def candidate_records_for_summary(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    date_text = date_from_summary_path(path)

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

    record_source_access(path, access_source="memory_extract:daily_summary")
    return records


def parse_frontmatter_header(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    return text[4:end]


def frontmatter_scalar(header: str, key: str) -> str | None:
    pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$")
    match = pattern.search(header)
    if not match:
        return None
    value = match.group(1).strip()
    return value.strip("'\"")


def frontmatter_truthy(header: str, key: str) -> bool:
    value = frontmatter_scalar(header, key)
    if value is None:
        return False
    return value.lower() in {"true", "yes", "1"}


def changed_markdown_paths_for_date(date_text: str) -> list[Path]:
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(PRIVATE_REPO_ROOT),
            "log",
            "--since",
            f"{date_text} 00:00:00",
            "--until",
            f"{date_text} 23:59:59",
            "--name-only",
            "--pretty=format:",
            "--",
            "*.md",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []

    deduped: list[Path] = []
    seen: set[Path] = set()
    for raw_line in proc.stdout.splitlines():
        relative = raw_line.strip()
        if not relative:
            continue
        path = (PRIVATE_REPO_ROOT / relative).resolve()
        if path in seen or not path.exists():
            continue
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def memory_type_for_doc_section(section: Section) -> str | None:
    label = f"{' '.join(section.parent_titles)} {section.title}".lower()
    if any(token in label for token in {"decision", "policy"}):
        return "decision"
    if any(token in label for token in {"commitment", "tomorrow", "next", "action", "plan"}):
        return "commitment"
    if any(token in label for token in {"status", "progress", "milestone", "update", "change"}):
        return "status_change"
    if any(token in label for token in {"pattern", "challenge", "lesson", "insight", "retro", "reflection"}):
        return "pattern"
    return None


def fallback_memory_type_for_doc(header: str) -> str | None:
    doc_type = (frontmatter_scalar(header, "doc_type") or "").lower()
    if "decision" in doc_type or "policy" in doc_type:
        return "decision"
    if "reflection" in doc_type or "retro" in doc_type or "pattern" in doc_type:
        return "pattern"
    if "plan" in doc_type or "commitment" in doc_type:
        return "commitment"
    if "status" in doc_type or "update" in doc_type:
        return "status_change"
    return None


def infer_doc_durability(memory_type: str) -> str:
    if memory_type == "decision":
        return "durable"
    if memory_type in {"commitment", "status_change"}:
        return "active"
    return "active"


def infer_doc_strength(memory_type: str) -> int:
    if memory_type in {"decision", "commitment", "status_change"}:
        return 3
    return 2


def record_from_doc_section(
    *,
    source_path: Path,
    date_text: str,
    section: Section,
    memory_type: str,
    text: str,
    index: int,
) -> dict[str, object]:
    relative = source_path.relative_to(PRIVATE_REPO_ROOT).as_posix()
    file_slug = slugify(relative.replace("/", "_"))
    id_parts = [memory_type, "doc", file_slug, slugify(section.title), date_text, str(index)]
    title = memory_title(memory_type, text, section, index)
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
        "durability": infer_doc_durability(memory_type),
        "strength": infer_doc_strength(memory_type),
        "last_reinforced_on": date_text,
        "source_ref": f"{relative}#{section.anchor}",
        "tags": [slugify(memory_type), slugify(section.title), "doc_source"],
        "supersedes": [],
    }


def candidate_records_for_memory_doc(path: Path, date_text: str) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    header = parse_frontmatter_header(text)
    if header is None or not frontmatter_truthy(header, "memory_eligible"):
        return []

    if path.is_relative_to(JOURNAL_SUMMARIES_DIR):
        return []

    fallback_type = fallback_memory_type_for_doc(header)
    fallback_section_allowlist = {
        "highlights",
        "key decisions",
        "tomorrow",
        "next steps",
        "action items",
        "challenges",
        "narrator notes",
        "status",
        "updates",
        "summary",
    }
    sections = parse_sections(text)
    records: list[dict[str, object]] = []

    for section in sections:
        bullets = bullet_lines(section)
        if not bullets:
            continue
        memory_type = memory_type_for_doc_section(section)
        if memory_type is None and fallback_type is not None:
            if section.title.strip().lower() not in fallback_section_allowlist:
                continue
            memory_type = fallback_type
        if memory_type is None:
            continue
        for index, bullet in enumerate(bullets[:5], start=1):
            records.append(
                record_from_doc_section(
                    source_path=path,
                    date_text=date_text,
                    section=section,
                    memory_type=memory_type,
                    text=bullet,
                    index=index,
                )
            )

    if records:
        records = records[:12]
        record_source_access(path, access_source="memory_extract:doc_source")
    return records


def candidate_records_for_changed_docs(date_text: str) -> tuple[list[dict[str, object]], int]:
    doc_paths = changed_markdown_paths_for_date(date_text)
    records: list[dict[str, object]] = []
    matched_docs = 0
    for path in doc_paths:
        doc_records = candidate_records_for_memory_doc(path, date_text)
        if doc_records:
            matched_docs += 1
            records.extend(doc_records)
    return records, matched_docs


def dedupe_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for record in records:
        record_id = str(record.get("id", ""))
        if not record_id or record_id in seen_ids:
            continue
        seen_ids.add(record_id)
        deduped.append(record)
    return deduped


def write_candidates(path: Path, records: Iterable[dict[str, object]]) -> Path:
    ensure_dir(CANDIDATES_DIR)
    date_text = date_from_summary_path(path)
    target_path = CANDIDATES_DIR / f"{date_text}.jsonl"
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
    parser.add_argument(
        "--also-docs",
        action="store_true",
        help="Also extract memory candidates from other memory-eligible markdown docs changed on the target date.",
    )
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
        date_text = date_from_summary_path(summary_path)
        summary_records = candidate_records_for_summary(summary_path)
        records = list(summary_records)
        doc_source_count = 0
        if args.also_docs:
            doc_records, doc_source_count = candidate_records_for_changed_docs(date_text)
            records.extend(doc_records)

        deduped_records = dedupe_records(records)
        out_path = write_candidates(summary_path, deduped_records)
        wrote_any = True
        print(
            f"{summary_path.relative_to(PRIVATE_REPO_ROOT)} -> "
            f"{out_path.relative_to(PRIVATE_REPO_ROOT)} "
            f"({len(deduped_records)} candidates; summary={len(summary_records)}; docs={doc_source_count})"
        )
        if args.print_records:
            for record in deduped_records:
                print(json.dumps(record, ensure_ascii=False))
    return 0 if wrote_any else 1


if __name__ == "__main__":
    raise SystemExit(main())
