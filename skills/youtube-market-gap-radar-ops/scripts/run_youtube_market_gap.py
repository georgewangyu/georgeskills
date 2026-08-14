#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run checkpointed YouTube low-base/high-demand search lanes."
    )
    parser.add_argument("--lane", action="append", default=[], help="Search lane; repeat as needed")
    parser.add_argument("--lane-file", type=Path, help="Newline-delimited search lanes")
    parser.add_argument("--youtube-bot-dir", default=os.environ.get("YOUTUBEBOT_DIR", ""))
    parser.add_argument("--max-subs", type=int, default=100_000)
    parser.add_argument("--min-views", type=int, default=50_000)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--content-type", choices=["any", "short", "long"], default="long")
    parser.add_argument(
        "--video-duration",
        choices=["any", "short", "medium", "long"],
        help="YouTube search duration bucket; medium is 4-20 minutes",
    )
    parser.add_argument("--language", default="en")
    parser.add_argument("--region", default="US")
    parser.add_argument("--max-search", type=int, default=50)
    parser.add_argument("--limit-per-lane", type=int, default=20)
    parser.add_argument("--min-outlier", type=float)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true", help="Rerun completed lanes")
    return parser.parse_args()


def load_lanes(args: argparse.Namespace) -> list[str]:
    lanes = list(args.lane)
    if args.lane_file:
        lanes.extend(
            line.strip()
            for line in args.lane_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    seen: set[str] = set()
    output: list[str] = []
    for lane in lanes:
        key = lane.strip().lower()
        if key and key not in seen:
            seen.add(key)
            output.append(lane.strip())
    return output


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"lanes": {}, "errors": {}, "videos": []}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"lanes": {}, "errors": {}, "videos": []}
    return parsed if isinstance(parsed, dict) else {"lanes": {}, "errors": {}, "videos": []}


def run_lane(args: argparse.Namespace, lane: str) -> tuple[list[dict[str, Any]], str | None]:
    command = [
        "node",
        "src/cli.js",
        "find",
        lane,
        "--max-subs",
        str(args.max_subs),
        "--min-views",
        str(args.min_views),
        "--days",
        str(args.days),
        "--type",
        args.content_type,
        "--max-search",
        str(args.max_search),
        "--limit",
        str(args.limit_per_lane),
        "--sort",
        "score",
        "--language",
        args.language,
        "--region",
        args.region,
        "--format",
        "json",
    ]
    if args.video_duration and args.video_duration != "any":
        command.extend(["--video-duration", args.video_duration])
    if args.min_outlier is not None:
        command.extend(["--min-outlier", str(args.min_outlier)])

    completed = subprocess.run(
        command,
        cwd=args.youtube_bot_dir,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "unknown collector error").strip()
        return [], message
    try:
        rows = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as error:
        return [], f"invalid JSON from youtubebot: {error}"
    if not isinstance(rows, list):
        return [], "unexpected non-list JSON from youtubebot"
    return rows, None


def age_days(published_at: Any) -> float | None:
    if not published_at:
        return None
    try:
        published = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - published).total_seconds() / 86400, 2)


def normalize(row: dict[str, Any], lane: str) -> dict[str, Any]:
    output = dict(row)
    output["searchLanes"] = [lane]
    output["ageDays"] = age_days(row.get("publishedAt"))
    return output


def dedupe_videos(lanes: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for lane, lane_state in lanes.items():
        for row in lane_state.get("videos", []):
            video_id = str(row.get("id", "")).strip()
            if not video_id:
                continue
            normalized = normalize(row, lane)
            if video_id not in merged:
                merged[video_id] = normalized
                continue
            existing = merged[video_id]
            existing["searchLanes"] = sorted(
                set(existing.get("searchLanes", [])) | {lane}
            )
            if float(row.get("score") or 0) > float(existing.get("score") or 0):
                lanes_found = existing["searchLanes"]
                merged[video_id] = normalized
                merged[video_id]["searchLanes"] = lanes_found
    return sorted(
        merged.values(),
        key=lambda row: float(row.get("score") or 0),
        reverse=True,
    )


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


def summarize_lane(videos: list[dict[str, Any]]) -> dict[str, Any]:
    strong = [row for row in videos if float(row.get("outlierScore") or 0) >= 10]
    channels: dict[str, int] = {}
    for row in strong:
        channel_id = str(row.get("channelId") or row.get("channel") or "")
        channels[channel_id] = channels.get(channel_id, 0) + 1
    repeated_channels = sum(1 for count in channels.values() if count >= 2)
    if len(channels) >= 2 or repeated_channels >= 1:
        demand_status = "confirmed"
    elif strong:
        demand_status = "discovery"
    else:
        demand_status = "unconfirmed"
    return {
        "candidateCount": len(videos),
        "strongVideoCount": len(strong),
        "independentStrongChannels": len(channels),
        "repeatStrongChannels": repeated_channels,
        "medianOutlierScore": median(
            [float(row.get("outlierScore") or 0) for row in strong]
        ),
        "medianSubscriberRatio": median(
            [float(row.get("subscriberRatio") or 0) for row in strong]
        ),
        "demandStatus": demand_status,
        "scarcityStatus": "unmeasured",
    }


def write_checkpoint(
    args: argparse.Namespace,
    checkpoint: dict[str, Any],
    requested_lanes: list[str],
) -> None:
    checkpoint["generatedAt"] = datetime.now(timezone.utc).isoformat()
    checkpoint["settings"] = {
        "maxSubscribers": args.max_subs,
        "minViews": args.min_views,
        "days": args.days,
        "contentType": args.content_type,
        "videoDuration": args.video_duration or "any",
        "language": args.language,
        "region": args.region,
        "maxSearch": args.max_search,
        "limitPerLane": args.limit_per_lane,
        "minOutlier": args.min_outlier,
    }
    checkpoint["requestedLanes"] = requested_lanes
    checkpoint["videos"] = dedupe_videos(checkpoint.get("lanes", {}))
    checkpoint["laneSummaries"] = {
        lane: summarize_lane(state.get("videos", []))
        for lane, state in checkpoint.get("lanes", {}).items()
        if state.get("status") == "completed"
    }
    checkpoint["completedLanes"] = sorted(
        lane
        for lane, state in checkpoint.get("lanes", {}).items()
        if state.get("status") == "completed"
    )
    checkpoint["failedLanes"] = sorted(checkpoint.get("errors", {}).keys())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    lanes = load_lanes(args)
    if not lanes:
        print("Provide at least one --lane or --lane-file.", file=sys.stderr)
        return 2
    if not args.youtube_bot_dir or not Path(args.youtube_bot_dir).is_dir():
        print("Set --youtube-bot-dir or YOUTUBEBOT_DIR.", file=sys.stderr)
        return 2

    checkpoint = load_checkpoint(args.out)
    checkpoint.setdefault("lanes", {})
    checkpoint.setdefault("errors", {})

    for lane in lanes:
        existing = checkpoint["lanes"].get(lane, {})
        if existing.get("status") == "completed" and not args.refresh:
            continue
        print(f"Scanning: {lane}", file=sys.stderr)
        videos, error = run_lane(args, lane)
        if error:
            checkpoint["errors"][lane] = error
            checkpoint["lanes"][lane] = {"status": "failed", "videos": []}
        else:
            checkpoint["errors"].pop(lane, None)
            checkpoint["lanes"][lane] = {"status": "completed", "videos": videos}
        write_checkpoint(args, checkpoint, lanes)

    print(
        json.dumps(
            {
                "output": str(args.out),
                "completedLanes": len(checkpoint.get("completedLanes", [])),
                "failedLanes": len(checkpoint.get("failedLanes", [])),
                "uniqueVideos": len(checkpoint.get("videos", [])),
            }
        )
    )
    return 0 if not checkpoint.get("failedLanes") else 1


if __name__ == "__main__":
    raise SystemExit(main())
