#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from datetime import datetime

# Viral Research Context (2026 Optimization)
VIRAL_GUIDELINES = """
2026 X Algorithm Optimization:
1. Hook: Strong first line (Counter-intuitive, Trauma-based, or high-value promise).
2. Shareability: Focus on reposts/bookmarks (How-to guides, insights).
3. No External Links: Keep links in the first reply.
4. Native Content: Mention specific technical results or trauma.
"""

def main():
    workspace_root = Path(__file__).resolve().parents[3]
    private_repo = workspace_root / "georgerepo"

    now = datetime.now()
    summary_path = private_repo / "journal" / "summaries" / now.strftime("%Y") / now.strftime("%m") / f"{now.strftime('%Y-%m-%d')}_Summary.md"

    x_feed_path = private_repo / "notes-private" / "social-media" / "x" / "home" / "latest.json"

    print(f"--- Daily Signal for {now.strftime('%Y-%m-%d')} ---")

    # 1. Journal Signal
    if not summary_path.exists():
        print(f"Warning: Summary not found at {summary_path}")
    else:
        content = summary_path.read_text()
        if "## Conversation Milestones" in content:
            milestones = content.split("## Conversation Milestones")[1].split("##")[0].strip()
            print("\n[Milestones]")
            print(milestones)
        if "## Highlights" in content:
            highlights = content.split("## Highlights")[1].split("##")[0].strip()
            print("\n[Highlights]")
            print(highlights)

    # 2. X Feed Context (Signal check)
    if x_feed_path.exists():
        try:
            with open(x_feed_path, 'r') as f:
                data = json.load(f)
                # Just show the first few for context
                print("\n[Recent X Feed Context]")
                for item in data[:5] if isinstance(data, list) else []:
                     text = item.get("full_text", item.get("text", ""))
                     print(f"- {text[:100]}...")
        except Exception as e:
            print(f"\n[X Context Error]: {e}")

    print("\n[Viral Guidelines]")
    print(VIRAL_GUIDELINES)

if __name__ == "__main__":
    main()
