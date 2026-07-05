#!/usr/bin/env python3
"""
Refresh and backfill compiled LLM-wiki pages.

This script intentionally mirrors the existing journal/memory pattern:
- use the daily summary as the stable chronological input
- produce reviewable candidate output
- auto-apply only low-risk page deltas
- optionally seed canonical topic pages from existing organized docs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from repo_paths import resolve_private_repo_root


PRIVATE_REPO_ROOT = resolve_private_repo_root()
WORKSPACE_ROOT = PRIVATE_REPO_ROOT.parent


def resolve_llm_wiki_root() -> Path:
    raw = os.environ.get("LLM_WIKI_ROOT", "").strip()
    if raw:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (WORKSPACE_ROOT / candidate).resolve()
        return candidate
    return WORKSPACE_ROOT / "llm-wiki"


AGENT_MANAGED_DIR = resolve_llm_wiki_root()
TOPICS_DIR = AGENT_MANAGED_DIR / "topics"
CANDIDATES_DIR = AGENT_MANAGED_DIR / "_candidates"
INDEXES_DIR = AGENT_MANAGED_DIR / "indexes"
REPORTS_DIR = AGENT_MANAGED_DIR / "reports"
CONVERSATION_NOTES_DIR = PRIVATE_REPO_ROOT / "notes-private" / "audio-conversations" / "notes"
SUMMARY_DIR = PRIVATE_REPO_ROOT / "journal" / "summaries"
SUMMARY_FILENAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_Summary\.md$")
LEVEL2_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", flags=re.MULTILINE)
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
INTERESTING_SECTIONS = {
    "Highlights",
    "Challenges",
    "Key Decisions",
    "Conversation Milestones",
    "Narrator Notes",
    "Reflections",
    "Today at a Glance",
}
CONVERSATION_NOTE_SECTIONS = {
    "What Mattered",
    "Concrete Takeaways",
    "Relationship Signal",
}
WORKSPACE_REPOS = tuple(
    repo.strip()
    for repo in os.environ.get(
        "KNOWLEDGE_WORKSPACE_REPOS",
        f"{PRIVATE_REPO_ROOT.name},liferepo,georgeskills",
    ).split(",")
    if repo.strip()
)
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
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "but",
    "by", "for", "from", "had", "has", "have", "if", "in", "into", "is",
    "it", "its", "of", "on", "or", "that", "the", "their", "them", "there",
    "this", "to", "too", "up", "was", "were", "with", "your", "you", "after",
    "before", "during", "over", "under", "than", "then", "when", "while",
    "still", "just", "also", "only", "more", "most", "some", "very", "not",
    "now", "out", "through", "across", "off", "again", "like", "into",
}
THEME_RULES = {
    "workflow_automation": {
        "keywords": {
            "workflow", "automation", "pipeline", "process", "system", "template",
            "loop", "orchestration", "compiler", "refresh", "index", "memory",
            "fanout", "heartbeat", "integration", "setup", "migration",
        },
        "label": "workflow design, automation, and operating loops",
    },
    "content_distribution": {
        "keywords": {
            "content", "social", "video", "script", "tiktok", "substack",
            "post", "posting", "editing", "hook", "creator", "x", "twitter",
            "youtube", "distribution", "publish", "publishing",
        },
        "label": "content production, hooks, and distribution",
    },
    "product_infra": {
        "keywords": {
            "openclaw", "agent", "agents", "infrastructure", "proposal", "tool",
            "tools", "mission", "control", "imessage", "workspace", "product",
            "prototype", "architecture", "deployment", "build",
        },
        "label": "product infrastructure and architecture work",
    },
    "learning_research": {
        "keywords": {
            "research", "learning", "course", "study", "paper", "papers",
            "concept", "concepts", "framework", "reading", "lecture", "education",
        },
        "label": "learning, research, and concept-building",
    },
    "health_behavior": {
        "keywords": {
            "adhd", "health", "sleep", "energy", "focus", "pattern", "patterns",
            "habit", "habits", "sprint", "curiosity", "detox", "battery",
        },
        "label": "health, attention, and behavior patterns",
    },
    "strategy_positioning": {
        "keywords": {
            "strategy", "positioning", "interview", "resume", "consulting",
            "offer", "client", "pricing", "business", "priority", "prioritized",
            "focus",
        },
        "label": "strategy, positioning, and prioritization",
    },
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


@dataclass
class TopicHealth:
    slug: str
    title: str
    evidence_count: int
    source_seed_count: int
    summary_quality: str
    current_understanding_quality: str
    top_themes: list[str]


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


def strip_source_suffix(text: str) -> str:
    text = re.sub(r"\s+Source:\s+`[^`]+`\s*$", "", text).strip()
    return text.strip()


def strip_code_spans(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"\1", text)


def section_bullets(text: str, title: str) -> list[str]:
    for section in parse_sections(text):
        base_title = re.sub(r"\s+\(Optional\)$", "", section.title).strip()
        if base_title == title:
            return bullet_lines(section)
    return []


def markdown_body(text: str) -> str:
    _, body = split_frontmatter(text)
    return body


def prose_sentences(text: str) -> list[str]:
    body = markdown_body(text)
    lines = []
    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("- ") or stripped.startswith("```"):
            continue
        lines.append(stripped)
    joined = " ".join(lines)
    sentences = re.split(r"(?<=[.!?])\s+", joined)
    return [s.strip() for s in sentences if len(s.strip()) > 30]


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


def source_seed_paths_for_page(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    header = parse_frontmatter_header(text)
    return frontmatter_list(header, "source_seed_paths") or frontmatter_list(header, "sources")


def readable_path_label(path: str) -> str:
    stem = Path(path).stem.replace("-", " ")
    return re.sub(r"\s+", " ", stem).strip()


def source_seed_snippets(seed_paths: list[str]) -> list[str]:
    snippets: list[str] = []
    for source_path in seed_paths[:8]:
        path = PRIVATE_REPO_ROOT / source_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        bullets = []
        for section in parse_sections(text):
            bullets.extend(bullet_lines(section))
            if len(bullets) >= 2:
                break
        for bullet in bullets[:2]:
            snippets.append(strip_code_spans(bullet))
        if len(snippets) >= 10:
            break
        for sentence in prose_sentences(text)[:1]:
            snippets.append(strip_code_spans(sentence))
            break
        if len(snippets) >= 10:
            break
    return snippets[:10]


def evidence_texts_for_page(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    bullets = [strip_code_spans(strip_source_suffix(b)) for b in section_bullets(text, "Important Evidence")]
    cleaned: list[str] = []
    for bullet in bullets:
        if not bullet or bullet.startswith("Seeded from "):
            continue
        if bullet not in cleaned:
            cleaned.append(bullet)
    return cleaned


def source_dates_for_page(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    refs = section_bullets(text, "Source Map") + section_bullets(text, "Important Evidence")
    dates: list[str] = []
    for line in refs:
        match = DATE_RE.search(line)
        if match:
            dates.append(match.group(1))
    return sorted(set(dates))


def word_counter(texts: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        normalized = strip_code_spans(text).lower()
        for token in re.findall(r"[a-z0-9][a-z0-9-]+", normalized):
            if len(token) < 4 or token in STOPWORDS or token in GENERIC_TOPIC_WORDS:
                continue
            counter[token] += 1
    return counter


def infer_theme_labels(topic: TopicPage, evidence_texts: list[str], source_snippets: list[str], seed_paths: list[str]) -> list[str]:
    haystacks = [topic.title.lower(), *topic.keywords, *[p.lower() for p in seed_paths], *[t.lower() for t in evidence_texts], *[t.lower() for t in source_snippets]]
    score_by_theme: dict[str, int] = {}
    for theme_name, theme in THEME_RULES.items():
        score = 0
        for keyword in theme["keywords"]:
            for haystack in haystacks:
                if keyword in haystack:
                    score += 1
        if score > 0:
            score_by_theme[theme_name] = score
    ordered = sorted(score_by_theme.items(), key=lambda item: (-item[1], item[0]))
    labels = [THEME_RULES[name]["label"] for name, _ in ordered[:3]]
    if not labels:
        frequent = [word for word, _ in word_counter(evidence_texts + source_snippets).most_common(3)]
        if frequent:
            labels.append(", ".join(frequent))
    return labels


def representative_evidence(evidence_texts: list[str], limit: int = 3) -> list[str]:
    if not evidence_texts:
        return []
    token_counts = word_counter(evidence_texts)
    scored: list[tuple[int, str]] = []
    for text in evidence_texts:
        score = sum(token_counts.get(token, 0) for token in re.findall(r"[a-z0-9][a-z0-9-]+", text.lower()))
        scored.append((score, text))
    selected: list[str] = []
    used_tokens: set[str] = set()
    for _, text in sorted(scored, key=lambda item: (-item[0], item[1])):
        tokens = {
            token for token in re.findall(r"[a-z0-9][a-z0-9-]+", text.lower())
            if len(token) >= 5 and token not in STOPWORDS
        }
        if selected and tokens and len(tokens & used_tokens) / max(len(tokens), 1) > 0.7:
            continue
        selected.append(text.rstrip(".") + ".")
        used_tokens |= tokens
        if len(selected) >= limit:
            break
    return selected[:limit]


def operational_signals(evidence_texts: list[str]) -> list[str]:
    joined = " ".join(evidence_texts).lower()
    bullets: list[str] = []
    if any(word in joined for word in ("prioritized", "primary focus", "postponed", "worth prioritizing", "committed to")):
        bullets.append("This topic repeatedly influences priority decisions instead of staying as a passive note archive.")
    if any(word in joined for word in ("reorganized", "workflow", "system", "template", "structure", "directory", "pipeline", "setup")):
        bullets.append("The work is trending toward explicit structure, repeatable workflows, and reusable assets rather than ad hoc notes.")
    if any(word in joined for word in ("tired", "fatigue", "slipped", "lost", "overloaded", "delay", "challenge")):
        bullets.append("Execution quality appears sensitive to energy and overload, so keeping scope controlled matters for follow-through.")
    if any(word in joined for word in ("shipped", "committed", "completed", "progress", "integrated", "landed", "edited", "captured")):
        bullets.append("There is repeated evidence of shipping and iteration, not just abstract planning.")
    deduped: list[str] = []
    for bullet in bullets:
        if bullet not in deduped:
            deduped.append(bullet)
    return deduped[:3]


def synthesize_summary(topic: TopicPage, evidence_texts: list[str], source_snippets: list[str], seed_paths: list[str], dates: list[str]) -> list[str]:
    theme_labels = infer_theme_labels(topic, evidence_texts, source_snippets, seed_paths)
    bullets = [
        f"{topic.title} is a recurring canonical topic grounded in {len(seed_paths)} seed documents and {len(evidence_texts)} accumulated evidence bullets."
    ]
    if theme_labels:
        if len(theme_labels) == 1:
            bullets.append(f"The strongest throughline is {theme_labels[0]}.")
        else:
            bullets.append(f"The strongest throughlines are {', '.join(theme_labels[:-1])}, and {theme_labels[-1]}.")
    if dates:
        bullets.append(f"Preserved evidence currently spans {dates[0]} through {dates[-1]}.")
    return [f"- {bullet}" for bullet in bullets[:3]]


def synthesize_current_understanding(topic: TopicPage, evidence_texts: list[str], source_snippets: list[str], seed_paths: list[str]) -> list[str]:
    bullets: list[str] = []
    theme_labels = infer_theme_labels(topic, evidence_texts, source_snippets, seed_paths)
    if theme_labels:
        bullets.append(
            f"{topic.title} currently appears to be centered on {', '.join(theme_labels[:2]) if len(theme_labels) > 1 else theme_labels[0]}."
        )
    reps = representative_evidence(evidence_texts, limit=2)
    for rep in reps:
        bullets.append(rep)
    for signal in operational_signals(evidence_texts):
        if signal not in bullets:
            bullets.append(signal)
    if len(bullets) < 3:
        for snippet in source_snippets[:3]:
            normalized = snippet.rstrip(".") + "."
            if normalized not in bullets:
                bullets.append(normalized)
            if len(bullets) >= 3:
                break
    deduped: list[str] = []
    for bullet in bullets:
        cleaned = strip_code_spans(bullet).strip()
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return [f"- {bullet}" for bullet in deduped[:4]]


def quality_for_section(bullets: list[str], placeholder_markers: list[str]) -> str:
    joined = " ".join(bullets).lower()
    if not bullets:
        return "missing"
    if any(marker in joined for marker in placeholder_markers):
        return "template"
    if len(bullets) < 2:
        return "thin"
    return "compiled"


def compile_topic_page(topic: TopicPage) -> bool:
    path = topic.path
    text = path.read_text(encoding="utf-8")
    seed_paths = source_seed_paths_for_page(path)
    evidence = evidence_texts_for_page(path)
    snippets = source_seed_snippets(seed_paths)
    dates = source_dates_for_page(path)

    summary_body = "\n".join(synthesize_summary(topic, evidence, snippets, seed_paths, dates))
    current_body = "\n".join(synthesize_current_understanding(topic, evidence, snippets, seed_paths))

    updated = upsert_level2_section(text, "Summary", summary_body)
    updated = upsert_level2_section(updated, "Current Understanding", current_body)

    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def build_health_report(topic_pages: list[TopicPage]) -> Path:
    ensure_dir(REPORTS_DIR)
    entries: list[TopicHealth] = []
    for topic in topic_pages:
        text = topic.path.read_text(encoding="utf-8")
        entries.append(
            TopicHealth(
                slug=topic.slug,
                title=topic.title,
                evidence_count=len(evidence_texts_for_page(topic.path)),
                source_seed_count=len(source_seed_paths_for_page(topic.path)),
                summary_quality=quality_for_section(
                    [strip_source_suffix(b) for b in section_bullets(text, "Summary")],
                    ["seeded from", "canonical synthesis"],
                ),
                current_understanding_quality=quality_for_section(
                    [strip_source_suffix(b) for b in section_bullets(text, "Current Understanding")],
                    ["good candidate for a maintained canonical page", "historical daily-summary replay"],
                ),
                top_themes=infer_theme_labels(topic, evidence_texts_for_page(topic.path), source_seed_snippets(source_seed_paths_for_page(topic.path)), source_seed_paths_for_page(topic.path)),
            )
        )
    entries.sort(key=lambda item: (item.current_understanding_quality, -item.evidence_count, item.title.lower()))
    lines = [
        "---",
        'title: "LLM Wiki Health Report"',
        "type: report",
        "status: active",
        f"created: {date.today().isoformat()}",
        f"updated: {date.today().isoformat()}",
        'sources: ["topics/"]',
        'tags: ["wiki", "report", "health"]',
        "---",
        "# LLM Wiki Health Report",
        "",
        "## Summary",
        "",
        f"- Total topic pages: {len(entries)}",
        f"- Compiled summaries: {sum(1 for entry in entries if entry.summary_quality == 'compiled')}",
        f"- Compiled current-understanding sections: {sum(1 for entry in entries if entry.current_understanding_quality == 'compiled')}",
        "",
        "## Page Health",
        "",
    ]
    for entry in entries:
        theme_text = ", ".join(entry.top_themes) if entry.top_themes else "no strong themes detected yet"
        lines.append(
            f"- `{entry.slug}` - evidence={entry.evidence_count}, seeds={entry.source_seed_count}, "
            f"summary={entry.summary_quality}, current_understanding={entry.current_understanding_quality}, themes={theme_text}"
        )
    path = REPORTS_DIR / "health-report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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
        f'title: "{seed.title}"\n'
        "type: topic\n"
        "status: active\n"
        f"created: {date.today().isoformat()}\n"
        f"updated: {date.today().isoformat()}\n"
        f"{frontmatter_block('sources', seed.source_paths)}\n"
        "tags:\n"
        '  - "wiki"\n'
        '  - "topic"\n'
        f'  - "{seed.slug}"\n'
        "---\n"
        f"# {seed.title}\n\n"
        "## Summary\n\n"
        f"- This page is the canonical LLM-wiki synthesis for `{seed.title}`.\n"
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
        "- `index.md`\n\n"
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
        f"- `{topic.path.relative_to(AGENT_MANAGED_DIR).as_posix()}` - canonical page for {topic.title}."
        for topic in sorted(topic_pages, key=lambda item: item.title.lower())
    )
    text = (
        "---\n"
        'title: "Knowledge Map"\n'
        "type: index\n"
        "status: active\n"
        f"created: {date.today().isoformat()}\n"
        f"updated: {date.today().isoformat()}\n"
        'sources: ["topics/"]\n'
        'tags: ["wiki", "index", "knowledge-map"]\n'
        "---\n"
        "# Knowledge Map\n\n"
        "## Summary\n\n"
        "- This index lists the canonical topic pages in `topics/`.\n"
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


def conversation_note_paths_for_date(date_text: str) -> list[Path]:
    year, month, _ = date_text.split("-")
    month_dir = CONVERSATION_NOTES_DIR / year / month
    if not month_dir.exists():
        return []
    return sorted(month_dir.glob(f"{date_text}-*.md"))


def conversation_note_signal(date_text: str) -> tuple[list[dict[str, str]], list[Path]]:
    note_paths = conversation_note_paths_for_date(date_text)
    signals: list[dict[str, str]] = []
    for note_path in note_paths:
        text = note_path.read_text(encoding="utf-8")
        rel = note_path.relative_to(PRIVATE_REPO_ROOT).as_posix()
        title = frontmatter_scalar(parse_frontmatter_header(text), "title") or note_path.stem.replace("-", " ").title()
        for section in parse_sections(text):
            base_title = re.sub(r"\s+\(Optional\)$", "", section.title).strip()
            if base_title not in CONVERSATION_NOTE_SECTIONS:
                continue
            for bullet in bullet_lines(section):
                signals.append(
                    {
                        "section": f"Conversation Note / {base_title}",
                        "text": f"{title}: {bullet}",
                        "source_ref": f"{rel}#{section.anchor}",
                    }
                )
    return signals, note_paths


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
    private_repo_prefix = f"{PRIVATE_REPO_ROOT.name}/"
    legacy_agent_managed_prefixes = (
        f"{private_repo_prefix}agent-managed/",
        f"{private_repo_prefix}knowledge/agent-managed/",
    )
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
                if full_rel.startswith(legacy_agent_managed_prefixes):
                    continue
                changed.append(full_rel)
        if target == date.today():
            for rel in current_workspace_changes(repo_dir):
                full_rel = f"{repo_name}/{rel}"
                if full_rel.startswith(legacy_agent_managed_prefixes):
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
        "page_path": topic.path.relative_to(AGENT_MANAGED_DIR).as_posix(),
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
    page_path = AGENT_MANAGED_DIR / str(candidate["page_path"])
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
    parser = argparse.ArgumentParser(description="Refresh compiled LLM-wiki knowledge from daily-summary signal.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--apply-safe", action="store_true", help="Apply low-risk updates directly to matched topic pages.")
    parser.add_argument("--print", action="store_true", dest="print_payload", help="Print candidate payload to stdout.")
    parser.add_argument("--seed-organized", action="store_true", help="Seed topic pages from organized knowledge and framework documents.")
    parser.add_argument("--refresh-seeds", action="store_true", help="Overwrite existing seeded topic pages with regenerated frontmatter and baseline content.")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild the LLM-wiki knowledge index page.")
    parser.add_argument("--backfill-all", action="store_true", help="Replay all available historical summaries.")
    parser.add_argument("--compile-synthesis", action="store_true", help="Rewrite `Summary` and `Current Understanding` for current topic pages.")
    parser.add_argument("--compile-all", action="store_true", help="Compile synthesis for all topic pages after any refresh/backfill work.")
    parser.add_argument("--health-report", action="store_true", help="Write a quality report for current topic pages.")
    return parser.parse_args()


def run_for_date(date_text: str, *, apply_safe: bool, print_payload: bool) -> tuple[int, list[str]]:
    summary_signals, summary_path = summary_signal(date_text)
    note_signals, note_paths = conversation_note_signal(date_text)
    signals = summary_signals + note_signals
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
        "summary_signal_count": len(summary_signals),
        "conversation_note_signal_count": len(note_signals),
        "conversation_note_count": len(note_paths),
        "conversation_note_paths": [path.relative_to(PRIVATE_REPO_ROOT).as_posix() for path in note_paths],
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

    print(f"LLM wiki candidates [{date_text}]: {len(candidates)} -> {candidate_path}")
    if applied_pages:
        print("applied safe updates:")
        for page in applied_pages:
            print(f"- {page}")

        log_path = AGENT_MANAGED_DIR / "log.md"
        if log_path.exists():
            log_entry = [f"## [{date_text}] auto-apply | Refresh LLM Wiki", f"- Applied safe updates to {len(applied_pages)} canonical pages."]
            for page in applied_pages:
                log_entry.append(f"  - `{Path(page).stem}`")
            with log_path.open("a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(log_entry) + "\n")
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
        print(f"rebuilt knowledge index: {index_path.relative_to(AGENT_MANAGED_DIR).as_posix()}")

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

    topic_pages = load_topic_pages()
    if args.compile_synthesis or args.compile_all:
        compiled = 0
        for topic in topic_pages:
            if compile_topic_page(topic):
                compiled += 1
        print(f"compiled topic pages: {compiled}/{len(topic_pages)}")

    if args.health_report or args.compile_all:
        report_path = build_health_report(load_topic_pages())
        print(f"wrote health report: {report_path.relative_to(AGENT_MANAGED_DIR).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
