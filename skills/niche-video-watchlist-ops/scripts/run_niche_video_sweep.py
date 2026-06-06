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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run targeted YouTube/TikTok/Instagram bot sweeps for niche video watchlists.")
    parser.add_argument("--config", type=Path, help="Private JSON config with lanes/watchlist/thresholds")
    parser.add_argument("--lane", action="append", default=[], help="Search lane. Can be repeated.")
    parser.add_argument("--youtube-bot-dir", default=os.environ.get("YOUTUBEBOT_DIR", ""))
    parser.add_argument("--tiktok-bot-dir", default=os.environ.get("TIKTOKBOT_DIR", ""))
    parser.add_argument("--ig-bot-dir", default=os.environ.get("IGBOT_DIR", ""))
    parser.add_argument("--max-base", type=int)
    parser.add_argument("--min-views", type=int)
    parser.add_argument("--days", type=int)
    parser.add_argument("--max-age-days", type=int, help="Filter output to videos published within this many days")
    parser.add_argument("--limit-per-lane", type=int)
    parser.add_argument("--platform", choices=["all", "both", "youtube", "tiktok", "instagram"], default="all")
    parser.add_argument("--tiktok-backend", choices=["auto", "python", "node"], help="TikTok web collection backend")
    parser.add_argument("--watchlist-only", action="store_true", help="Skip search lanes and only run supported watchlist collectors")
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
        platform = str(item.get("platform", "")).lower()
        if handle and platform not in {"instagram", "ig"}:
            lanes.append(str(handle))
    if args.watchlist_only:
        lanes = []
    return {
        "lanes": dedupe(lanes),
        "watchlist": config.get("watchlist", []),
        "youtube_bot_dir": args.youtube_bot_dir or bot_dirs.get("youtube", ""),
        "tiktok_bot_dir": args.tiktok_bot_dir or bot_dirs.get("tiktok", ""),
        "ig_bot_dir": args.ig_bot_dir or bot_dirs.get("instagram", "") or bot_dirs.get("ig", ""),
        "max_base": int(args.max_base if args.max_base is not None else thresholds.get("max_base", 250000)),
        "min_views": int(args.min_views if args.min_views is not None else thresholds.get("min_views", 10000)),
        "days": int(args.days if args.days is not None else thresholds.get("days", 365)),
        "max_age_days": int(args.max_age_days if args.max_age_days is not None else thresholds["max_age_days"]) if args.max_age_days is not None or thresholds.get("max_age_days") else None,
        "limit_per_lane": int(args.limit_per_lane if args.limit_per_lane is not None else thresholds.get("limit_per_lane", 10)),
        "platform": args.platform,
        "tiktok_backend": str(args.tiktok_backend if args.tiktok_backend is not None else thresholds.get("tiktok_backend", "auto")),
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


def collect(settings: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    include_youtube = settings["platform"] in {"all", "both", "youtube"}
    include_tiktok = settings["platform"] in {"all", "both", "tiktok"}
    include_instagram = settings["platform"] in {"all", "instagram"}
    for lane in settings["lanes"]:
        if include_youtube and settings["youtube_bot_dir"]:
            command = [
                "node", "src/cli.js", "find", lane,
                "--type", "short",
                "--video-duration", "short",
                "--days", str(settings["max_age_days"] or settings["days"]),
                "--max-subs", str(settings["max_base"]),
                "--min-views", str(settings["min_views"]),
                "--max-search", "30",
                "--limit", str(settings["limit_per_lane"]),
                "--sort", "subscriber-ratio",
                "--format", "json",
            ]
            rows.extend(row for row in (normalize(row, lane, "youtube") for row in run_json(command, settings["youtube_bot_dir"])) if within_age(row, settings["max_age_days"]))
        if include_tiktok and settings["tiktok_bot_dir"]:
            command = [
                "node", "src/cli.js", "web-search", lane,
                "--max-results", "20",
                "--limit", str(settings["limit_per_lane"]),
                "--max-followers", str(settings["max_base"]),
                "--min-views", str(settings["min_views"]),
                "--sort", "views-per-follower",
                "--backend", settings["tiktok_backend"],
                "--format", "json",
            ]
            rows.extend(row for row in (normalize(row, lane, "tiktok") for row in run_json(command, settings["tiktok_bot_dir"])) if within_age(row, settings["max_age_days"]))
        if include_instagram and settings["ig_bot_dir"]:
            command = [
                "node", "src/cli.js", "private-search", lane,
                "--max-results", "20",
                "--limit", str(settings["limit_per_lane"]),
                "--max-followers", str(settings["max_base"]),
                "--min-views", str(settings["min_views"]),
                "--sort", "views-per-follower",
                "--format", "json",
            ]
            rows.extend(row for row in (normalize(row, lane, "instagram") for row in run_json(command, settings["ig_bot_dir"])) if within_age(row, settings["max_age_days"]))
    if include_instagram and settings["ig_bot_dir"]:
        for item in settings.get("watchlist", []):
            platform = str(item.get("platform", "")).lower()
            handle = str(item.get("handle", "")).strip()
            if platform not in {"instagram", "ig"} or not handle:
                continue
            command = [
                "node", "src/cli.js", "private-profile", handle,
                "--max-results", "20",
                "--limit", str(settings["limit_per_lane"]),
                "--min-views", str(settings["min_views"]),
                "--sort", "views-per-follower",
                "--format", "json",
            ]
            lane = f"instagram watchlist:{handle}"
            rows.extend(row for row in (normalize(row, lane, "instagram") for row in run_json(command, settings["ig_bot_dir"])) if within_age(row, settings["max_age_days"]))
    return sorted(rows, key=lambda row: float(row.get("ratio") or 0), reverse=True)


def main() -> int:
    args = parse_args()
    settings = merge_args(args, load_config(args.config))
    if not settings["lanes"] and not settings.get("watchlist"):
        print("No lanes or watchlist entries provided. Use --lane or --config.", file=sys.stderr)
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
