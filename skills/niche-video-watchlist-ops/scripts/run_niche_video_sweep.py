#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from video_observations import observation
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "account-video-watchlist-ops" / "scripts"))
from run_account_video_watchlist import run_json as bounded_run_json, empty_health, finalize_health


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
    parser.add_argument("--platform", choices=["all", "both", "youtube", "tiktok", "instagram"], default="youtube")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--failure-threshold", type=int, default=2)
    parser.add_argument("--health-out", type=Path)
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
        "timeout_seconds": args.timeout_seconds,
        "failure_threshold": args.failure_threshold,
        "health_out": args.health_out,
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
    legacy = {
        "platform": platform,
        "lane": lane,
        "creator": row.get("creator") or row.get("channelTitle") or row.get("channel") or "",
        "base": base,
        "views": row.get("views"),
        "ratio": ratio if ratio is not None else row.get("score"),
        "outlier": row.get("outlierScore"),
        "published_at": published_at,
        "age_days": age_days,
        "title": row.get("caption") or row.get("title") or "",
        "url": row.get("url"),
        "source": row.get("source"),
    }

    return observation({**row, **legacy}, platform, datetime.now(timezone.utc).isoformat())


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
    rows = []
    health = empty_health()
    failures = {platform: 0 for platform in health}
    platform = settings["platform"]
    enabled = {"youtube", "tiktok"} if platform == "both" else set(health) if platform == "all" else {platform}

    def capture(command, source, lane):
        state = health[source]
        if failures[source] >= settings["failure_threshold"]:
            state["skipped_after_circuit_breaker"] += 1
            return
        state["attempted"] += 1
        bot_key = {"youtube": "youtube_bot_dir", "tiktok": "tiktok_bot_dir", "instagram": "ig_bot_dir"}[source]
        raw, error = bounded_run_json(command, settings[bot_key], settings["timeout_seconds"])
        if error:
            failures[source] += 1
            state["failed"] += 1
            state["errors"].append({"lane": lane, "error": error})
            print(f"{source} {lane}: {error}", file=sys.stderr)
            return
        failures[source] = 0
        state["succeeded"] += 1
        state["rows_returned"] += len(raw)
        rows.extend(row for row in (normalize(row, lane, source) for row in raw)
                    if within_age(row, settings["max_age_days"]))

    # Keyword discovery is YouTube/optional Instagram only. TikTok embeds expose
    # tracked profiles, not a search index. Never reinterpret a handle as a keyword.
    for lane in settings["lanes"]:
        if "youtube" in enabled and settings["youtube_bot_dir"]:
            capture(["node", "src/cli.js", "find", lane, "--type", "short",
                     "--video-duration", "short", "--days", str(settings["max_age_days"] or settings["days"]),
                     "--max-subs", str(settings["max_base"]), "--min-views", str(settings["min_views"]),
                     "--max-search", "30", "--limit", str(settings["limit_per_lane"]),
                     "--sort", "outlier", "--format", "json"], "youtube", lane)
        # One failed Instagram search canary closes search; profiles remain eligible.
        if "instagram" in enabled and settings["ig_bot_dir"] and not health["instagram"]["failed"]:
            capture(["node", "src/cli.js", "private-search", lane, "--max-results", "20",
                     "--limit", str(settings["limit_per_lane"]), "--min-views", str(settings["min_views"]),
                     "--format", "json"], "instagram", lane)
    for item in settings.get("watchlist", []):
        source = {"ig": "instagram", "yt": "youtube"}.get(str(item.get("platform", "")).lower(), str(item.get("platform", "")).lower())
        handle = str(item.get("handle", "")).strip()
        if source not in enabled or not handle or not settings.get({"youtube": "youtube_bot_dir", "tiktok": "tiktok_bot_dir", "instagram": "ig_bot_dir"}[source]):
            continue
        if source == "youtube":
            ref = item.get("channel_id") or item.get("url") or handle
            command = ["node", "src/cli.js", "find", "--channel-ref", ref, "--type", "any",
                       "--days", str(settings["max_age_days"] or settings["days"]),
                       "--min-views", str(settings["min_views"]), "--limit", str(settings["limit_per_lane"]),
                       "--sort", "outlier", "--format", "json"]
        else:
            command = ["node", "src/cli.js", "profile-feed" if source == "tiktok" else "private-profile", handle,
                       "--max-results", "20", "--limit", str(settings["limit_per_lane"]),
                       "--min-views", str(settings["min_views"]), "--format", "json"]
        capture(command, source, f"{source} watchlist:{handle}")
    finalize_health(health)
    for state in health.values():
        if state["status"] == "success" and not state["rows_returned"]:
            state["status"] = "degraded"
            state["errors"].append({"error": "collector returned no usable rows"})
    settings["health"] = health
    # Baseline lift and ratio are distinct evidence; missing values stay missing.
    return sorted(rows, key=lambda row: (float(row.get("outlier") or -1), float(row.get("ratio") or -1)), reverse=True)


def main() -> int:
    args = parse_args()
    settings = merge_args(args, load_config(args.config))
    if not settings["lanes"] and not settings.get("watchlist"):
        print("No lanes or watchlist entries provided. Use --lane or --config.", file=sys.stderr)
        return 2
    if settings["timeout_seconds"] <= 0 or settings["failure_threshold"] <= 0:
        raise ValueError("Timeout and failure threshold must be positive")
    settings["out"].parent.mkdir(parents=True, exist_ok=True)
    if settings["out"].exists():
        raise FileExistsError(f"Refusing existing output: {settings['out']}")
    rows = collect(settings)
    if settings["health_out"]:
        settings["health_out"].parent.mkdir(parents=True, exist_ok=True)
        settings["health_out"].write_text(json.dumps(settings["health"], indent=2) + "\n")
    # Attempts are immutable. An unavailable run must not replace a good snapshot.
    with settings["out"].open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {settings['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
