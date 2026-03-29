#!/usr/bin/env python3
"""
Backfill a standard YAML header across markdown docs.

This script is intentionally conservative:
- preserves existing frontmatter and only adds missing keys
- skips configured paths (for example raw exports / external repos)
- avoids rewriting files when no changes are needed
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ROOTS = ("liferepo", "georgerepo")
DEFAULT_SKIP_PREFIXES = (
    "georgerepo/notes-private/",
    "georgerepo/openclaw/",
    "georgerepo/projects/mission-control/app/node_modules/",
)
ALWAYS_SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
STANDARD_SCHEMA = "doc-frontmatter-v1"


@dataclass
class DocMeta:
    repo: str
    rel_path: Path
    title: str
    description: str
    doc_type: str
    doc_status: str
    memory_eligible: bool
    memory_priority: str


def doc_tags_lines(meta: DocMeta) -> list[str]:
    domain = meta.rel_path.parts[0] if meta.rel_path.parts else "root"
    visibility = "private" if meta.repo == "georgerepo" else "public"
    return [
        "doc_tags:",
        f"  - {yaml_scalar(f'domain:{domain}')}",
        f"  - {yaml_scalar(f'visibility:{visibility}')}",
        f"  - {yaml_scalar(f'type:{meta.doc_type}')}",
    ]


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    header = text[4:end]
    body = text[end + 5 :]
    return header, body


def infer_title(body: str, rel_path: Path) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    stem = rel_path.stem.replace("_", " ").replace("-", " ").strip()
    return stem.title() or "Untitled Document"


def infer_description(body: str, title: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("```", "---")):
            continue
        cleaned = re.sub(r"^[-*]\s+", "", stripped)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            return cleaned[:180]
    return f"Reference document for {title}."


def infer_doc_type(rel: Path) -> str:
    parts = [p.lower() for p in rel.parts]
    name = rel.name
    if re.match(r"^\d{4}-\d{2}-\d{2}_Summary\.md$", name):
        return "daily_summary"
    if "sprints" in parts:
        return "sprint"
    if "reflections" in parts:
        return "reflection"
    if "memory" in parts:
        return "memory_doc"
    if name.startswith("AGENT") or name == "AGENTS.md":
        return "agent_spec"
    if name == "README.md":
        return "readme"
    if name == "IMPROVEMENTS.md":
        return "improvements"
    if "workflow" in name.lower():
        return "workflow_spec"
    if rel.parts:
        return f"{parts[0]}_doc"
    return "doc"


def infer_doc_status(rel: Path) -> str:
    lowered = rel.as_posix().lower()
    if any(token in lowered for token in ("/_legacy/", "/archive/", "/archives/")):
        return "archived"
    return "active"


def infer_memory_eligible(rel: Path, doc_type: str) -> bool:
    path = rel.as_posix().lower()
    if doc_type in {"agent_spec", "readme", "improvements", "workflow_spec"}:
        return False
    if "templates/" in path:
        return False
    if doc_type in {"daily_summary", "sprint", "reflection", "memory_doc"}:
        return True
    preferred_prefixes = (
        "journal/",
        "knowledge/",
        "principles/",
        "projects/",
        "career/",
        "business/",
        "health/",
        "housing/",
        "writing/",
        "deep-exploration/",
        "social-media/",
    )
    return path.startswith(preferred_prefixes)


def infer_memory_priority(doc_type: str, memory_eligible: bool) -> str:
    if not memory_eligible:
        return "low"
    if doc_type in {"daily_summary", "sprint", "reflection", "memory_doc"}:
        return "high"
    return "medium"


def build_doc_meta(repo: str, rel_path: Path, body: str) -> DocMeta:
    title = infer_title(body, rel_path)
    description = infer_description(body, title)
    doc_type = infer_doc_type(rel_path)
    memory_eligible = infer_memory_eligible(rel_path, doc_type)
    return DocMeta(
        repo=repo,
        rel_path=rel_path,
        title=title,
        description=description,
        doc_type=doc_type,
        doc_status=infer_doc_status(rel_path),
        memory_eligible=memory_eligible,
        memory_priority=infer_memory_priority(doc_type, memory_eligible),
    )


def yaml_scalar(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def header_has_key(header: str, key: str) -> bool:
    return re.search(rf"(?m)^{re.escape(key)}\s*:", header) is not None


def standard_header_lines(meta: DocMeta) -> list[str]:
    doc_id = f"{meta.repo}/{meta.rel_path.with_suffix('').as_posix()}"
    return [
        f"doc_schema: {yaml_scalar(STANDARD_SCHEMA)}",
        f"doc_id: {yaml_scalar(doc_id)}",
        f"doc_type: {yaml_scalar(meta.doc_type)}",
        f"doc_status: {yaml_scalar(meta.doc_status)}",
        f"title: {yaml_scalar(meta.title)}",
        f"description: {yaml_scalar(meta.description)}",
        f"memory_eligible: {'true' if meta.memory_eligible else 'false'}",
        f"memory_priority: {yaml_scalar(meta.memory_priority)}",
    ]


def merge_header(header: str, meta: DocMeta) -> tuple[str, bool]:
    changed = False
    lines = header.splitlines()
    for std_line in standard_header_lines(meta):
        key = std_line.split(":", 1)[0]
        if header_has_key(header, key):
            continue
        lines.append(std_line)
        changed = True
    if not header_has_key(header, "doc_tags"):
        lines.extend(doc_tags_lines(meta))
        changed = True
    merged = "\n".join(lines).strip("\n")
    return merged, changed


def build_new_file_text(meta: DocMeta, body: str) -> str:
    header = "\n".join([*standard_header_lines(meta), *doc_tags_lines(meta)])
    return f"---\n{header}\n---\n{body.lstrip()}"


def should_skip(path: Path, *, workspace_root: Path, skip_prefixes: tuple[str, ...]) -> bool:
    rel = path.relative_to(workspace_root).as_posix()
    if any(part in ALWAYS_SKIP_PARTS for part in path.parts):
        return True
    return any(rel.startswith(prefix) for prefix in skip_prefixes)


def iter_markdown_files(root: Path, *, workspace_root: Path, skip_prefixes: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.md"):
        if should_skip(path, workspace_root=workspace_root, skip_prefixes=skip_prefixes):
            continue
        files.append(path)
    return sorted(files)


def apply_to_file(path: Path, *, workspace_root: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    repo = path.relative_to(workspace_root).parts[0]
    rel_path = path.relative_to(workspace_root / repo)
    header, body = split_frontmatter(text)
    meta = build_doc_meta(repo, rel_path, body if header is None else body)

    if header is None:
        new_text = build_new_file_text(meta, body)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            return True
        return False

    merged, changed = merge_header(header, meta)
    if not changed:
        return False
    new_text = f"---\n{merged}\n---\n{body}"
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill standard YAML frontmatter across markdown docs.")
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        help="Workspace-relative root to process (repeatable). Defaults to liferepo + georgerepo.",
    )
    parser.add_argument(
        "--skip-prefix",
        action="append",
        dest="skip_prefixes",
        help="Workspace-relative path prefix to skip (repeatable).",
    )
    parser.add_argument("--write", action="store_true", help="Write changes (default is dry-run).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = Path(__file__).resolve().parents[4]
    roots = args.roots or list(DEFAULT_ROOTS)
    skip_prefixes = tuple(args.skip_prefixes or DEFAULT_SKIP_PREFIXES)

    all_files: list[Path] = []
    for root_name in roots:
        root = (workspace_root / root_name).resolve()
        if not root.exists():
            print(f"missing root: {root_name}")
            continue
        all_files.extend(iter_markdown_files(root, workspace_root=workspace_root, skip_prefixes=skip_prefixes))

    changed = 0
    for path in all_files:
        if args.write and apply_to_file(path, workspace_root=workspace_root):
            changed += 1
        elif not args.write:
            text = path.read_text(encoding="utf-8")
            header, body = split_frontmatter(text)
            repo = path.relative_to(workspace_root).parts[0]
            rel_path = path.relative_to(workspace_root / repo)
            meta = build_doc_meta(repo, rel_path, body if header is None else body)
            if header is None:
                changed += 1
            else:
                _, would_change = merge_header(header, meta)
                if would_change:
                    changed += 1

    mode = "updated" if args.write else "would update"
    print(f"{mode}: {changed} files (scanned {len(all_files)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
