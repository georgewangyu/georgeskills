#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import date, datetime

# Viral Research Context (2026 Optimization)
VIRAL_GUIDELINES = """
2026 X Algorithm Optimization:
1. Hook: Strong first line (Counter-intuitive, Trauma-based, or high-value promise).
2. Shareability: Focus on reposts/bookmarks (How-to guides, insights).
3. No External Links: Keep links in the first reply.
4. Native Content: Mention specific technical results or trauma.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print journal and feed context for drafting X posts."
    )
    parser.add_argument(
        "--private-repo",
        help=(
            "Private repo root. Defaults to LIFEREPO_PRIVATE_ROOT or "
            "PRIVATE_REPO_ROOT."
        ),
    )
    parser.add_argument(
        "--summary-path",
        help="Explicit daily-summary input path (or X_POST_SUMMARY_PATH).",
    )
    parser.add_argument(
        "--feed-path",
        help="Explicit X feed JSON input path (or X_POST_FEED_PATH).",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Summary date in YYYY-MM-DD (default: today).",
    )
    return parser.parse_args()


def optional_path(cli_value: str | None, env_key: str) -> Path | None:
    raw = cli_value or os.environ.get(env_key, "").strip()
    return Path(raw).expanduser().resolve() if raw else None


def resolve_private_repo(cli_value: str | None) -> Path | None:
    raw = cli_value
    if not raw:
        for key in ("LIFEREPO_PRIVATE_ROOT", "PRIVATE_REPO_ROOT"):
            raw = os.environ.get(key, "").strip()
            if raw:
                break
    return Path(raw).expanduser().resolve() if raw else None


def resolve_inputs(args: argparse.Namespace) -> tuple[datetime, Path, Path | None]:
    try:
        run_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError as exc:
        raise SystemExit(f"Invalid --date value {args.date!r}; expected YYYY-MM-DD") from exc

    private_repo = resolve_private_repo(args.private_repo)
    summary_path = optional_path(args.summary_path, "X_POST_SUMMARY_PATH")
    feed_path = optional_path(args.feed_path, "X_POST_FEED_PATH")

    if summary_path is None:
        if private_repo is None:
            raise SystemExit(
                "Set --summary-path, --private-repo, LIFEREPO_PRIVATE_ROOT, "
                "or PRIVATE_REPO_ROOT."
            )
        summary_path = (
            private_repo
            / "journal"
            / "summaries"
            / run_date.strftime("%Y")
            / run_date.strftime("%m")
            / f"{run_date.strftime('%Y-%m-%d')}_Summary.md"
        )

    if feed_path is None and private_repo is not None:
        feed_path = (
            private_repo
            / "notes-private"
            / "social-media"
            / "x"
            / "home"
            / "latest.json"
        )

    return run_date, summary_path, feed_path


def main() -> int:
    args = parse_args()
    now, summary_path, x_feed_path = resolve_inputs(args)

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
    if x_feed_path and x_feed_path.exists():
        try:
            with x_feed_path.open(encoding="utf-8") as f:
                data = json.load(f)
                # Just show the first few for context
                print("\n[Recent X Feed Context]")
                for item in data[:5] if isinstance(data, list) else []:
                     text = item.get("full_text", item.get("text", ""))
                     print(f"- {text[:100]}...")
        except (OSError, json.JSONDecodeError) as e:
            print(f"\n[X Context Error]: {e}")

    print("\n[Viral Guidelines]")
    print(VIRAL_GUIDELINES)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
