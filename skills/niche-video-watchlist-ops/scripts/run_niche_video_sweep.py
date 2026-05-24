#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run targeted YouTube/TikTok bot sweeps for niche video watchlists.")
    parser.add_argument("--config", type=Path, help="Private JSON config with lanes/watchlist/thresholds")
    parser.add_argument("--lane", action="append", default=[], help="Search lane. Can be repeated.")
    parser.add_argument("--youtube-bot-dir", default=os.environ.get("YOUTUBEBOT_DIR", ""))
    parser.add_argument("--tiktok-bot-dir", default=os.environ.get("TIKTOKBOT_DIR", ""))
    parser.add_argument("--max-base", type=int, default=250000)
    parser.add_argument("--min-views", type=int, default=10000)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--limit-per-lane", type=int, default=10)
    parser.add_argument("--platform", choices=["both", "youtube", "tiktok"], default="both")
    parser.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    return parser.parse_args()


def load_config(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def merge_args(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    thresholds = config.get("thresholds", {})
    bot_dirs = config.get("bot_dirs", {})
    lanes = list(config.get("lanes", [])) + list(args.lane)
    for item in config.get("watchlist", []):
        handle = item.get("handle")
        if handle:
            lanes.append(str(handle))
    return {
        "lanes": dedupe(lanes),
        "youtube_bot_dir": args.youtube_bot_dir or bot_dirs.get("youtube", ""),
        "tiktok_bot_dir": args.tiktok_bot_dir or bot_dirs.get("tiktok", ""),
        "max_base": int(thresholds.get("max_base", args.max_base)),
        "min_views": int(thresholds.get("min_views", args.min_views)),
        "days": int(thresholds.get("days", args.days)),
        "limit_per_lane": int(thresholds.get("limit_per_lane", args.limit_per_lane)),
        "platform": args.platform,
        "out": args.out,
    }


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value.strip())
    return output


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
    base = row.get("followers") if platform == "tiktok" else row.get("subscribers")
    ratio = row.get("viewsPerFollower") if platform == "tiktok" else row.get("subscriberRatio")
    return {
        "platform": platform,
        "lane": lane,
        "creator": row.get("creator") or row.get("channelTitle") or row.get("channel") or "",
        "base": base,
        "views": row.get("views"),
        "ratio": ratio or row.get("score"),
        "outlier": row.get("outlierScore"),
        "title": row.get("caption") or row.get("title") or "",
        "url": row.get("url"),
        "source": row.get("source"),
    }


def collect(settings: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lane in settings["lanes"]:
        if settings["platform"] in {"both", "youtube"} and settings["youtube_bot_dir"]:
            command = [
                "node", "src/cli.js", "find", lane,
                "--type", "short",
                "--video-duration", "short",
                "--days", str(settings["days"]),
                "--max-subs", str(settings["max_base"]),
                "--min-views", str(settings["min_views"]),
                "--max-search", "30",
                "--limit", str(settings["limit_per_lane"]),
                "--sort", "subscriber-ratio",
                "--format", "json",
            ]
            rows.extend(normalize(row, lane, "youtube") for row in run_json(command, settings["youtube_bot_dir"]))
        if settings["platform"] in {"both", "tiktok"} and settings["tiktok_bot_dir"]:
            command = [
                "node", "src/cli.js", "web-search", lane,
                "--max-results", "20",
                "--limit", str(settings["limit_per_lane"]),
                "--max-followers", str(settings["max_base"]),
                "--min-views", str(settings["min_views"]),
                "--sort", "views-per-follower",
                "--format", "json",
            ]
            rows.extend(normalize(row, lane, "tiktok") for row in run_json(command, settings["tiktok_bot_dir"]))
    return sorted(rows, key=lambda row: float(row.get("ratio") or 0), reverse=True)


def main() -> int:
    args = parse_args()
    settings = merge_args(args, load_config(args.config))
    if not settings["lanes"]:
        print("No lanes provided. Use --lane or --config.", file=sys.stderr)
        return 2
    settings["out"].parent.mkdir(parents=True, exist_ok=True)
    rows = collect(settings)
    with settings["out"].open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {settings['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
