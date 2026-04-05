#!/usr/bin/env python3
"""
Initialize the Karpathy LLM-Wiki structure in agent-managed layer.
Creates index.md, log.md, and migrates references from knowledge-map.md
"""

import os
import re
from datetime import datetime
from pathlib import Path

def get_workspace_root() -> Path:
    current = Path(__file__).resolve()
    # georgeskills/skills/knowledge-ops/scripts/init_llm_wiki.py -> 5 parents up is workspace root
    return current.parents[4]

def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"\A---\n.*?\n---\n", text, flags=re.DOTALL)
    if not match:
        return "", text
    return text[:match.end()], text[match.end():]

def parse_frontmatter_header(text: str) -> str:
    frontmatter, _ = split_frontmatter(text)
    return frontmatter

def frontmatter_scalar(header: str, key: str):
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", header, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"')

def main():
    workspace = get_workspace_root()
    agent_managed = workspace / "georgerepo" / "agent-managed"
    topics_dir = agent_managed / "topics"
    projects_dir = agent_managed / "projects"
    entities_dir = agent_managed / "entities"

    index_file = agent_managed / "index.md"
    log_file = agent_managed / "log.md"
    old_map_file = agent_managed / "indexes" / "knowledge-map.md"

    # Step 1: Collect pages
    pages = []

    for d in [topics_dir, projects_dir, entities_dir]:
        if not d.exists():
            continue
        for path in d.glob("*.md"):
            if path.name == "README.md":
                continue
            text = path.read_text(encoding="utf-8")
            header = parse_frontmatter_header(text)
            title = frontmatter_scalar(header, "title") or path.stem.replace("-", " ").title()
            description = frontmatter_scalar(header, "description") or "No description provided."
            pages.append({
                "path": path.relative_to(agent_managed).as_posix(),
                "title": title,
                "description": description,
                "category": d.name
            })

            # Step 2: Rewrite knowledge-map references
            new_text = text.replace("agent-managed/indexes/knowledge-map.md", "index.md")
            new_text = new_text.replace("../../indexes/knowledge-map.md", "../../index.md")
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
                print(f"Updated references in {path.name}")

    # Step 3: Write index.md
    index_lines = [
        "---",
        'doc_schema: "doc-frontmatter-v1"',
        'doc_id: "georgerepo/agent-managed/index"',
        'doc_type: "knowledge_index"',
        'doc_status: "active"',
        'title: "LLM-Wiki Index"',
        'description: "Canonical entry point for agent-managed knowledge. L1 Progressive Disclosure."',
        "doc_tags:",
        '  - "domain:knowledge"',
        '  - "visibility:private"',
        '  - "type:knowledge_index"',
        "---",
        "# LLM-Wiki Index",
        "",
        "> **Agent Instruction:** Always read this file first (L1) before loading full topic pages (L3).",
        ""
    ]

    # Group by category
    categories = {}
    for p in pages:
        categories.setdefault(p["category"], []).append(p)

    for cat in sorted(categories.keys()):
        index_lines.append(f"## {cat.title()}")
        index_lines.append("")
        for p in sorted(categories[cat], key=lambda x: x["title"]):
            index_lines.append(f"- [{p['title']}]({p['path']}) - {p['description']}")
        index_lines.append("")

    index_file.write_text("\n".join(index_lines), encoding="utf-8")
    print(f"Generated {index_file}")

    # Step 4: Write log.md if not exists
    today = datetime.now().strftime("%Y-%m-%d")
    log_content = f"## [{today}] ingest | Wiki Initialization\n- Generated index.md with {len(pages)} canonical pages.\n- Deprecated knowledge-map.md.\n"
    if not log_file.exists():
        log_lines = [
            "---",
            'doc_schema: "doc-frontmatter-v1"',
            'doc_id: "georgerepo/agent-managed/log"',
            'doc_type: "knowledge_log"',
            'doc_status: "active"',
            'title: "LLM-Wiki Log"',
            'description: "Chronological append-only registry of wiki modifications."',
            "doc_tags:",
            '  - "domain:knowledge"',
            '  - "visibility:private"',
            '  - "type:knowledge_log"',
            "---",
            "# LLM-Wiki Operations Log",
            "",
            log_content
        ]
        log_file.write_text("\n".join(log_lines), encoding="utf-8")
        print(f"Generated {log_file}")
    else:
        # Append
        text = log_file.read_text(encoding="utf-8")
        text += f"\n{log_content}"
        log_file.write_text(text, encoding="utf-8")
        print(f"Appended to {log_file}")

    # Step 5: Remove old map
    if old_map_file.exists():
        old_map_file.unlink()
        print(f"Removed {old_map_file}")

if __name__ == "__main__":
    main()
