#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

DEFAULT_LANES = [
    "money hacks",
    "paycheck budget",
    "moving to a new city",
    "day in my life",
    "work from home comedy",
    "AI tools",
    "career change",
    "food budget",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a broad YouTube/TikTok/Instagram trend radar sweep.")
    parser.add_argument("--lane", action="append", default=[], help="Broad search lane. Can be repeated.")
    parser.add_argument("--youtube-bot-dir", default=os.environ.get("YOUTUBEBOT_DIR", ""))
    parser.add_argument("--tiktok-bot-dir", default=os.environ.get("TIKTOKBOT_DIR", ""))
    parser.add_argument("--ig-bot-dir", default=os.environ.get("IGBOT_DIR", ""))
    parser.add_argument("--max-base", type=int, default=300000)
    parser.add_argument("--min-views", type=int, default=25000)
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--max-age-days", type=int, help="Filter output to videos published within this many days")
    parser.add_argument("--limit-per-lane", type=int, default=8)
    parser.add_argument("--platform", choices=["all", "both", "youtube", "tiktok", "instagram"], default="all")
    parser.add_argument("--include-tiktok-trending", action="store_true")
    parser.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    return parser.parse_args()


def run_json(command: list[str], cwd: str) -> list[dict[str, Any]]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if completed.returncode != 0:
        print(completed.stderr.strip() or completed.stdout.strip(), file=sys.stderr)
        return []
    try:
        parsed = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as error:
        print(f"failed to parse JSON from {' '.join(command)}: {error}", file=sys.stderr)
        return []
    return parsed if isinstance(parsed, list) else []


def normalize(row: dict[str, Any], lane: str, platform: str) -> dict[str, Any]:
    if platform in {"tiktok", "instagram"}:
        base = row.get("followers")
        ratio = row.get("viewsPerFollower")
        published_at = row.get("postedAt")
    else:
        base = row.get("subscribers")
        ratio = row.get("subscriberRatio")
        published_at = row.get("publishedAt")
    age_days = compute_age_days(published_at)
    return {
        "platform": platform,
        "lane": lane,
        "creator": row.get("creator") or row.get("channelTitle") or row.get("channel") or "",
        "base": base,
        "views": row.get("views"),
        "ratio": ratio or row.get("score"),
        "outlier": row.get("outlierScore"),
        "published_at": published_at,
        "age_days": age_days,
        "title": row.get("caption") or row.get("title") or "",
        "url": row.get("url"),
        "source": row.get("source"),
    }


def compute_age_days(value: Any) -> float | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        published = datetime.fromisoformat(text)
    except ValueError:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - published).total_seconds() / 86400, 2)


def within_age(row: dict[str, Any], max_age_days: int | None) -> bool:
    if max_age_days is None:
        return True
    age_days = row.get("age_days")
    return age_days is not None and float(age_days) <= max_age_days


def collect(args: argparse.Namespace) -> list[dict[str, Any]]:
    lanes = args.lane or DEFAULT_LANES
    rows: list[dict[str, Any]] = []
    include_youtube = args.platform in {"all", "both", "youtube"}
    include_tiktok = args.platform in {"all", "both", "tiktok"}
    include_instagram = args.platform in {"all", "instagram"}
    for lane in lanes:
        if include_youtube and args.youtube_bot_dir:
            command = [
                "node", "src/cli.js", "find", lane,
                "--type", "short",
                "--video-duration", "short",
                "--days", str(args.max_age_days or args.days),
                "--max-subs", str(args.max_base),
                "--min-views", str(args.min_views),
                "--max-search", "30",
                "--limit", str(args.limit_per_lane),
                "--sort", "subscriber-ratio",
                "--format", "json",
            ]
            rows.extend(row for row in (normalize(row, lane, "youtube") for row in run_json(command, args.youtube_bot_dir)) if within_age(row, args.max_age_days))
        if include_tiktok and args.tiktok_bot_dir:
            command = [
                "node", "src/cli.js", "web-search", lane,
                "--max-results", "20",
                "--limit", str(args.limit_per_lane),
                "--max-followers", str(args.max_base),
                "--min-views", str(args.min_views),
                "--sort", "views-per-follower",
                "--format", "json",
            ]
            rows.extend(row for row in (normalize(row, lane, "tiktok") for row in run_json(command, args.tiktok_bot_dir)) if within_age(row, args.max_age_days))
        if include_instagram and args.ig_bot_dir:
            command = [
                "node", "src/cli.js", "private-search", lane,
                "--max-results", "20",
                "--limit", str(args.limit_per_lane),
                "--max-followers", str(args.max_base),
                "--min-views", str(args.min_views),
                "--sort", "views-per-follower",
                "--format", "json",
            ]
            rows.extend(row for row in (normalize(row, lane, "instagram") for row in run_json(command, args.ig_bot_dir)) if within_age(row, args.max_age_days))
    if args.include_tiktok_trending and args.tiktok_bot_dir and include_tiktok:
        command = [
            "node", "src/cli.js", "web-trending",
            "--max-results", "30",
            "--limit", str(args.limit_per_lane),
            "--max-followers", str(args.max_base),
            "--min-views", str(args.min_views),
            "--sort", "views-per-follower",
            "--format", "json",
        ]
        rows.extend(row for row in (normalize(row, "tiktok trending", "tiktok") for row in run_json(command, args.tiktok_bot_dir)) if within_age(row, args.max_age_days))
    return sorted(rows, key=lambda row: float(row.get("ratio") or 0), reverse=True)


def main() -> int:
    args = parse_args()
    if not args.youtube_bot_dir and not args.tiktok_bot_dir and not args.ig_bot_dir:
        print("Set --youtube-bot-dir/--tiktok-bot-dir/--ig-bot-dir or YOUTUBEBOT_DIR/TIKTOKBOT_DIR/IGBOT_DIR.", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = collect(args)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
