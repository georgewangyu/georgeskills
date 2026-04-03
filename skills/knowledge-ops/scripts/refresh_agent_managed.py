#!/usr/bin/env python3
"""
Refresh and backfill agent-managed compiled knowledge pages.

This script intentionally mirrors the existing journal/memory pattern:
- use the daily summary as the stable chronological input
- produce reviewable candidate output
- auto-apply only low-risk page deltas
- optionally seed canonical topic pages from existing organized docs
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from repo_paths import resolve_private_repo_root


PRIVATE_REPO_ROOT = resolve_private_repo_root()
WORKSPACE_ROOT = PRIVATE_REPO_ROOT.parent
AGENT_MANAGED_DIR = PRIVATE_REPO_ROOT / "knowledge" / "agent-managed"
TOPICS_DIR = AGENT_MANAGED_DIR / "topics"
CANDIDATES_DIR = AGENT_MANAGED_DIR / "_candidates"
INDEXES_DIR = AGENT_MANAGED_DIR / "indexes"
SUMMARY_DIR = PRIVATE_REPO_ROOT / "journal" / "summaries"
SUMMARY_FILENAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_Summary\.md$")
LEVEL2_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", flags=re.MULTILINE)
INTERESTING_SECTIONS = {
    "Highlights",
    "Challenges",
    "Key Decisions",
    "Conversation Milestones",
    "Narrator Notes",
    "Reflections",
    "Today at a Glance",
}
WORKSPACE_REPOS = ("georgerepo", "liferepo", "georgeskills")
SEED_SCAN_ROOTS = (
    PRIVATE_REPO_ROOT / "knowledge",
    PRIVATE_REPO_ROOT / "deep-exploration" / "frameworks",
)
SEED_EXCLUDED_DIRS = {
    "agent-managed",
    "prompts",
    "_archive",
    ".git",
    "__pycache__",
}
SEED_EXCLUDED_FILENAMES = {
    "README.md",
    "IMPROVEMENTS.md",
    "PRIVATE-knowledge.md",
    "PRIVATE-deep-exploration.md",
    "EXPLORATION_QUEUE.md",
    "OPENCLAW_EXPLORATION_QUEUE.md",
}
GENERIC_TOPIC_WORDS = {
    "agent",
    "managed",
    "knowledge",
    "layer",
    "current",
    "best",
    "synthesis",
    "topic",
    "topics",
    "readme",
    "research",
    "results",
    "summary",
    "analysis",
    "docs",
    "design",
    "paper",
    "papers",
    "history",
    "concepts",
    "other",
    "findings",
    "framework",
    "frameworks",
    "memory",
    "current",
}


@dataclass
class Section:
    title: str
    anchor: str
    lines: list[str]


@dataclass
class TopicPage:
    path: Path
    title: str
    slug: str
    keywords: list[str]


@dataclass
class SeedTopic:
    slug: str
    title: str
    description: str
    source_paths: list[str]
    keywords: list[str]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def markdown_anchor(title: str) -> str:
    return slugify(title.replace("/", " ")) or "section"


def titleize_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def summary_path_for_date(date_text: str) -> Path:
    year, month, _ = date_text.split("-")
    return SUMMARY_DIR / year / month / f"{date_text}_Summary.md"


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"\A---\n.*?\n---\n", text, flags=re.DOTALL)
    if not match:
        return "", text
    return text[:match.end()], text[match.end():]


def extract_level2_headers(text: str) -> dict[str, tuple[int, int]]:
    matches = list(LEVEL2_HEADER_RE.finditer(text))
    sections: dict[str, tuple[int, int]] = {}
    for idx, match in enumerate(matches):
        title = re.sub(r"\s+\(Optional\)$", "", match.group(1).strip()).strip()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[title] = (match.start(), end)
    return sections


def upsert_level2_section(text: str, title: str, body: str) -> str:
    frontmatter, markdown_body = split_frontmatter(text)
    sections = extract_level2_headers(markdown_body)
    block = f"## {title}\n\n{body.strip()}\n"

    if title in sections:
        start, end = sections[title]
        updated_body = (
            markdown_body[:start].rstrip("\n")
            + "\n\n"
            + block
            + "\n"
            + markdown_body[end:].lstrip("\n")
        )
        return frontmatter + updated_body.lstrip("\n")

    updated_body = markdown_body.rstrip("\n") + "\n\n" + block
    return frontmatter + updated_body.lstrip("\n")


def append_unique_bullets(text: str, title: str, bullets: list[str]) -> str:
    if not bullets:
        return text
    frontmatter, markdown_body = split_frontmatter(text)
    sections = extract_level2_headers(markdown_body)
    existing_lines: list[str] = []
    if title in sections:
        start, end = sections[title]
        section_text = markdown_body[start:end]
        for raw_line in section_text.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("- "):
                existing_lines.append(stripped)
    merged = existing_lines[:]
    for bullet in bullets:
        stripped = bullet.strip()
        if not stripped.startswith("- "):
            stripped = f"- {stripped}"
        if stripped not in merged:
            merged.append(stripped)
    body = "\n".join(merged) if merged else "- Not logged yet."
    return upsert_level2_section(frontmatter + markdown_body, title, body)


def parse_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    for raw_line in text.splitlines():
        heading_match = re.match(r"^(#{2,6})\s+(.*)$", raw_line)
        if heading_match:
            if current is not None:
                sections.append(current)
            title = heading_match.group(2).strip()
            current = Section(title=title, anchor=markdown_anchor(title), lines=[])
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
            text = re.sub(r"\s+", " ", match.group(1)).strip()
            if text:
                bullets.append(text)
    return bullets


def parse_frontmatter_header(text: str) -> str:
    frontmatter, _ = split_frontmatter(text)
    return frontmatter


def frontmatter_list(header: str, key: str) -> list[str]:
    lines = header.splitlines()
    values: list[str] = []
    collecting = False
    for line in lines:
        if collecting:
            stripped = line.strip()
            if stripped.startswith("- "):
                values.append(stripped[2:].strip().strip('"'))
                continue
            if not line.startswith(" "):
                break
        if re.match(rf"^{re.escape(key)}:\s*$", line):
            collecting = True
    return values


def frontmatter_scalar(header: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", header, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"')


def frontmatter_block(key: str, values: list[str], *, indent: str = "") -> str:
    if not values:
        return f"{indent}{key}: []"
    lines = [f"{indent}{key}:"]
    for value in values:
        lines.append(f'{indent}  - "{value}"')
    return "\n".join(lines)


def topic_keywords(path: Path, title: str, header: str) -> list[str]:
    keywords = frontmatter_list(header, "agent_managed_keywords")
    seed_paths = frontmatter_list(header, "source_seed_paths")
    if not keywords:
        keywords.extend(
            part
            for part in re.split(r"[^a-z0-9]+", path.stem.lower())
            if len(part) > 3 and part not in GENERIC_TOPIC_WORDS
        )
        keywords.extend(
            part
            for part in re.split(r"[^a-z0-9]+", title.lower())
            if len(part) > 3 and part not in GENERIC_TOPIC_WORDS
        )
        for seed_path in seed_paths:
            keywords.extend(
                part
                for part in re.split(r"[^a-z0-9]+", seed_path.lower())
                if len(part) > 3 and part not in GENERIC_TOPIC_WORDS
            )
    deduped: list[str] = []
    for keyword in keywords:
        normalized = keyword.strip().lower()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def load_topic_pages() -> list[TopicPage]:
    if not TOPICS_DIR.exists():
        return []
    pages: list[TopicPage] = []
    for path in sorted(TOPICS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        header = parse_frontmatter_header(text)
        title = frontmatter_scalar(header, "title") or path.stem.replace("-", " ").title()
        pages.append(
            TopicPage(
                path=path,
                title=title,
                slug=slugify(path.stem),
                keywords=topic_keywords(path, title, header),
            )
        )
    return pages


def summary_dates() -> list[str]:
    dates: list[str] = []
    if not SUMMARY_DIR.exists():
        return dates
    for path in sorted(SUMMARY_DIR.rglob("*_Summary.md")):
        match = SUMMARY_FILENAME_RE.search(path.name)
        if match:
            dates.append(match.group(1))
    return dates


def is_excluded_seed_path(path: Path) -> bool:
    if path.name in SEED_EXCLUDED_FILENAMES:
        return True
    if not path.suffix.lower() == ".md":
        return True
    if path.name.startswith("PRIVATE-"):
        return True
    parts = set(path.parts)
    return any(part in SEED_EXCLUDED_DIRS for part in parts)


def collect_seed_groups() -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for root in SEED_SCAN_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            if is_excluded_seed_path(path):
                continue
            rel = path.relative_to(PRIVATE_REPO_ROOT).as_posix()
            if rel.startswith("knowledge/"):
                parts = rel.split("/")
                if len(parts) >= 3:
                    topic_key = parts[1]
                else:
                    topic_key = path.stem
            else:
                topic_key = path.stem
            groups.setdefault(slugify(topic_key), []).append(path)
    return groups


def infer_seed_keywords(slug: str, title: str, source_paths: list[str]) -> list[str]:
    keywords: list[str] = [slug.replace("-", " "), slug, title.lower()]
    for source_path in source_paths:
        parts = Path(source_path).parts
        informative_parts = [
            part.lower()
            for part in parts
            if len(part) > 3
            and part.lower() not in GENERIC_TOPIC_WORDS
            and part.lower() not in {"knowledge", "deep-exploration", "explorations"}
        ]
        if informative_parts:
            keywords.append(informative_parts[0].replace("-", " "))
    deduped: list[str] = []
    for keyword in keywords:
        normalized = re.sub(r"\s+", " ", keyword.strip().lower())
        if len(normalized) < 4:
            continue
        if normalized not in deduped:
            deduped.append(normalized)
    return deduped[:20]


def build_seed_topics() -> list[SeedTopic]:
    seeds: list[SeedTopic] = []
    for slug, paths in sorted(collect_seed_groups().items()):
        unique_paths = [
            p.relative_to(PRIVATE_REPO_ROOT).as_posix()
            for p in sorted(paths)
            if p.is_file()
        ]
        if not unique_paths:
            continue
        title = titleize_slug(slug)
        if slug == "adhd-learnings":
            title = "ADHD Learnings"
        elif slug == "ai-agents":
            title = "AI Agents"
        elif slug == "ai-crash-course":
            title = "AI Crash Course"
        elif slug == "openclaw":
            title = "OpenClaw"
        description = (
            f"Current best synthesis of the {title} topic, seeded from existing organized repo documents."
        )
        seeds.append(
            SeedTopic(
                slug=slug,
                title=title,
                description=description,
                source_paths=unique_paths[:20],
                keywords=infer_seed_keywords(slug, title, unique_paths),
            )
        )
    return seeds


def seed_page_content(seed: SeedTopic) -> str:
    source_map = "\n".join(
        f"- `{source_path}` - seeded from an existing organized document."
        for source_path in seed.source_paths
    )
    return (
        "---\n"
        'doc_schema: "doc-frontmatter-v1"\n'
        f'doc_id: "georgerepo/knowledge/agent-managed/topics/{seed.slug}"\n'
        'doc_type: "knowledge_doc"\n'
        'doc_status: "active"\n'
        f'title: "{seed.title}"\n'
        f'description: "{seed.description}"\n'
        "memory_eligible: true\n"
        'memory_priority: "medium"\n'
        "doc_tags:\n"
        '  - "domain:knowledge"\n'
        '  - "visibility:private"\n'
        '  - "type:knowledge_doc"\n'
        f"{frontmatter_block('agent_managed_keywords', seed.keywords)}\n"
        f"{frontmatter_block('source_seed_paths', seed.source_paths)}\n"
        "---\n"
        f"# {seed.title}\n\n"
        "## Summary\n\n"
        f"- This page is the canonical agent-managed synthesis for `{seed.title}`.\n"
        f"- It was seeded from {len(seed.source_paths)} existing organized documents and should absorb future cross-session understanding.\n\n"
        "## Current Understanding\n\n"
        "- This topic already exists across prior knowledge and exploration artifacts, which makes it a good candidate for a maintained canonical page.\n"
        "- Historical daily-summary replay should enrich the evidence trail while keeping the page readable and inspectable.\n"
        "- Higher-risk rewrites to core synthesis should happen only when there is enough repeated signal to justify them.\n\n"
        "## Important Evidence\n\n"
        f"- Seeded from {len(seed.source_paths)} organized source documents already present in the repo.\n\n"
        "## Open Questions\n\n"
        "- What parts of this topic are stable enough to promote into tighter current-understanding bullets?\n"
        "- Which recurring subtopics deserve their own canonical child pages later?\n\n"
        "## Related Pages\n\n"
        "- `knowledge/agent-managed/indexes/knowledge-map.md`\n\n"
        "## Source Map\n\n"
        f"{source_map}\n"
    )


def ensure_seed_topic_pages(*, overwrite: bool = False) -> list[Path]:
    ensure_dir(TOPICS_DIR)
    updated: list[Path] = []
    for seed in build_seed_topics():
        path = TOPICS_DIR / f"{seed.slug}.md"
        if path.exists() and not overwrite:
            continue
        path.write_text(seed_page_content(seed), encoding="utf-8")
        updated.append(path)
    return updated


def rebuild_index_page(topic_pages: list[TopicPage]) -> Path:
    ensure_dir(INDEXES_DIR)
    path = INDEXES_DIR / "knowledge-map.md"
    entries = "\n".join(
        f"- `{topic.path.relative_to(PRIVATE_REPO_ROOT).as_posix()}` - canonical page for {topic.title}."
        for topic in sorted(topic_pages, key=lambda item: item.title.lower())
    )
    text = (
        "---\n"
        'doc_schema: "doc-frontmatter-v1"\n'
        'doc_id: "georgerepo/knowledge/agent-managed/indexes/knowledge-map"\n'
        'doc_type: "knowledge_index"\n'
        'doc_status: "active"\n'
        'title: "Knowledge Map"\n'
        'description: "Index of canonical agent-managed topic pages."\n'
        "memory_eligible: true\n"
        'memory_priority: "medium"\n'
        "doc_tags:\n"
        '  - "domain:knowledge"\n'
        '  - "visibility:private"\n'
        '  - "type:knowledge_index"\n'
        "---\n"
        "# Knowledge Map\n\n"
        "## Summary\n\n"
        "- This index lists the canonical topic pages in `knowledge/agent-managed/topics/`.\n"
        "- Topic pages should hold current-best synthesis, while day-by-day chronology remains in `journal/`.\n\n"
        "## Topic Pages\n\n"
        f"{entries}\n"
    )
    path.write_text(text, encoding="utf-8")
    return path


def summary_signal(date_text: str) -> tuple[list[dict[str, str]], Path]:
    summary_path = summary_path_for_date(date_text)
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary for {date_text}: {summary_path}")
    text = summary_path.read_text(encoding="utf-8")
    signals: list[dict[str, str]] = []
    for section in parse_sections(text):
        base_title = re.sub(r"\s+\(Optional\)$", "", section.title).strip()
        if base_title not in INTERESTING_SECTIONS:
            continue
        for bullet in bullet_lines(section):
            signals.append(
                {
                    "section": base_title,
                    "text": bullet,
                    "source_ref": f"{summary_path.relative_to(PRIVATE_REPO_ROOT).as_posix()}#{section.anchor}",
                }
            )
    return signals, summary_path


def current_workspace_changes(repo_dir: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if path and not path.endswith("/"):
            changed.append(path)
    return changed


def changed_files_for_date(date_text: str) -> list[str]:
    target = datetime.strptime(date_text, "%Y-%m-%d").date()
    next_day = target + timedelta(days=1)
    changed: list[str] = []
    for repo_name in WORKSPACE_REPOS:
        repo_dir = WORKSPACE_ROOT / repo_name
        if not (repo_dir / ".git").exists():
            continue
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "log",
                "--since",
                f"{date_text}T00:00:00",
                "--until",
                f"{next_day.isoformat()}T00:00:00",
                "--name-only",
                "--pretty=format:",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            rel = line.strip()
            if rel:
                full_rel = f"{repo_name}/{rel}"
                if full_rel.startswith("georgerepo/knowledge/agent-managed/"):
                    continue
                changed.append(full_rel)
        if target == date.today():
            for rel in current_workspace_changes(repo_dir):
                full_rel = f"{repo_name}/{rel}"
                if full_rel.startswith("georgerepo/knowledge/agent-managed/"):
                    continue
                changed.append(full_rel)
    deduped: list[str] = []
    for path in changed:
        if path not in deduped:
            deduped.append(path)
    return deduped


def build_candidate(topic: TopicPage, signals: list[dict[str, str]], changed_files: list[str]) -> dict[str, object] | None:
    score = 0
    matched_signals: list[dict[str, str]] = []
    for signal in signals:
        haystack = signal["text"].lower()
        matched_keywords: list[str] = []
        for keyword in topic.keywords:
            if len(keyword) < 3:
                continue
            if keyword in haystack:
                score += 2
                matched_keywords.append(keyword)
        if matched_keywords:
            matched_signals.append(signal)

    matched_files: list[str] = []
    for rel_path in changed_files:
        haystack = rel_path.lower()
        for keyword in topic.keywords:
            if len(keyword) < 3:
                continue
            if keyword in haystack:
                score += 1
                matched_files.append(rel_path)
                break

    if score <= 0:
        return None

    evidence_bullets: list[str] = []
    source_map_bullets: list[str] = []
    seen_source_map: set[str] = set()
    for signal in matched_signals[:8]:
        evidence_bullets.append(f'- {signal["text"]} Source: `{signal["source_ref"]}`')
        bullet = f'- `{signal["source_ref"]}` - matched current topic keywords via `{signal["section"]}`.'
        if bullet not in seen_source_map:
            source_map_bullets.append(bullet)
            seen_source_map.add(bullet)
    for rel_path in matched_files[:8]:
        bullet = f'- `{rel_path}` - changed in the workspace on the target date and matched the topic keyword set.'
        if bullet not in seen_source_map:
            source_map_bullets.append(bullet)
            seen_source_map.add(bullet)

    return {
        "topic_slug": topic.slug,
        "topic_title": topic.title,
        "page_path": topic.path.relative_to(PRIVATE_REPO_ROOT).as_posix(),
        "score": score,
        "matched_signal_count": len(matched_signals),
        "matched_file_count": len(matched_files),
        "matched_signals": matched_signals,
        "matched_files": matched_files[:20],
        "safe_updates": {
            "important_evidence": evidence_bullets,
            "source_map": source_map_bullets,
        },
    }


def write_candidates(date_text: str, payload: dict[str, object]) -> Path:
    ensure_dir(CANDIDATES_DIR)
    path = CANDIDATES_DIR / f"{date_text}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def apply_safe_updates(candidate: dict[str, object], *, date_text: str) -> bool:
    page_path = PRIVATE_REPO_ROOT / str(candidate["page_path"])
    if not page_path.exists():
        return False
    text = page_path.read_text(encoding="utf-8")
    safe_updates = candidate.get("safe_updates", {})
    changed = False

    important = list(safe_updates.get("important_evidence", []))
    updated = append_unique_bullets(text, "Important Evidence", important)
    if updated != text:
        text = updated
        changed = True

    source_map = list(safe_updates.get("source_map", []))
    updated = append_unique_bullets(text, "Source Map", source_map)
    if updated != text:
        text = updated
        changed = True

    if changed:
        page_path.write_text(text, encoding="utf-8")
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh agent-managed compiled knowledge from daily-summary signal.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--apply-safe", action="store_true", help="Apply low-risk updates directly to matched topic pages.")
    parser.add_argument("--print", action="store_true", dest="print_payload", help="Print candidate payload to stdout.")
    parser.add_argument("--seed-organized", action="store_true", help="Seed topic pages from organized knowledge and framework documents.")
    parser.add_argument("--refresh-seeds", action="store_true", help="Overwrite existing seeded topic pages with regenerated frontmatter and baseline content.")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild the agent-managed knowledge index page.")
    parser.add_argument("--backfill-all", action="store_true", help="Replay all available historical summaries.")
    return parser.parse_args()


def run_for_date(date_text: str, *, apply_safe: bool, print_payload: bool) -> tuple[int, list[str]]:
    signals, summary_path = summary_signal(date_text)
    changed_files = changed_files_for_date(date_text)
    topic_pages = load_topic_pages()

    candidates = []
    for topic in topic_pages:
        candidate = build_candidate(topic, signals, changed_files)
        if candidate is not None:
            candidates.append(candidate)

    payload = {
        "date": date_text,
        "summary_path": summary_path.relative_to(PRIVATE_REPO_ROOT).as_posix(),
        "signal_count": len(signals),
        "changed_file_count": len(changed_files),
        "candidates": candidates,
    }
    candidate_path = write_candidates(date_text, payload)

    applied_pages: list[str] = []
    if apply_safe:
        for candidate in candidates:
            if apply_safe_updates(candidate, date_text=date_text):
                applied_pages.append(str(candidate["page_path"]))

    print(f"agent-managed candidates [{date_text}]: {len(candidates)} -> {candidate_path}")
    if applied_pages:
        print("applied safe updates:")
        for page in applied_pages:
            print(f"- {page}")
    else:
        print("applied safe updates: none")

    if print_payload:
        print(json.dumps(payload, indent=2))
    return len(candidates), applied_pages


def main() -> int:
    args = parse_args()

    if args.seed_organized or args.refresh_seeds:
        created = ensure_seed_topic_pages(overwrite=args.refresh_seeds)
        action_label = "refreshed topic pages" if args.refresh_seeds else "seeded topic pages"
        print(f"{action_label}: {len(created)}")
        for path in created:
            print(f"- {path.relative_to(PRIVATE_REPO_ROOT).as_posix()}")

    topic_pages = load_topic_pages()
    if args.rebuild_index or args.seed_organized or args.refresh_seeds:
        index_path = rebuild_index_page(topic_pages)
        print(f"rebuilt knowledge index: {index_path.relative_to(PRIVATE_REPO_ROOT).as_posix()}")

    if args.backfill_all:
        dates = summary_dates()
    else:
        date_text = args.date
        if date_text.strip().lower() == "today":
            date_text = date.today().isoformat()
        dates = [date_text]

    total_candidates = 0
    total_applied = 0
    for date_text in dates:
        candidate_count, applied_pages = run_for_date(
            date_text,
            apply_safe=args.apply_safe,
            print_payload=args.print_payload and len(dates) == 1,
        )
        total_candidates += candidate_count
        total_applied += len(applied_pages)

    if len(dates) > 1:
        print(
            f"backfill summary: dates={len(dates)} candidates={total_candidates} "
            f"applied_updates={total_applied}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
