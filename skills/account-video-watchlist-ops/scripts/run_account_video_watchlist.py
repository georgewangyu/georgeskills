#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check a markdown account watchlist for high-view short-form videos.")
    parser.add_argument("--watchlist", type=Path, required=True, help="Private markdown watchlist path")
    parser.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    parser.add_argument("--previous", type=Path, help="Previous JSONL output for new-link comparison")
    parser.add_argument("--youtube-bot-dir", default=os.environ.get("YOUTUBEBOT_DIR", ""))
    parser.add_argument("--tiktok-bot-dir", default=os.environ.get("TIKTOKBOT_DIR", ""))
    parser.add_argument("--ig-bot-dir", default=os.environ.get("IGBOT_DIR", ""))
    parser.add_argument("--tiktok-web-backend", choices=["auto", "python", "node"], default="auto")
    parser.add_argument("--tiktok-web-browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    parser.add_argument("--tiktok-web-headless", choices=["true", "false"], default="true")
    parser.add_argument("--tiktok-web-mute-audio", choices=["true", "false"], default=os.environ.get("TIKTOK_WEB_MUTE_AUDIO", "true"), help="Mute TikTok browser automation audio")
    parser.add_argument("--platform", choices=["all", "youtube", "tiktok", "instagram"], default="all")
    parser.add_argument("--min-views", type=int, default=100000)
    parser.add_argument("--max-age-days", type=int, default=45)
    parser.add_argument("--limit-per-account", type=int, default=10)
    parser.add_argument("--max-base", type=int, default=10000000)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    return parser.parse_args()


def parse_watchlist(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in cells):
            continue
        if headers is None:
            headers = [normalize_key(cell) for cell in cells]
            continue
        row = {headers[index]: cells[index] if index < len(cells) else "" for index in range(len(headers))}
        platform = row.get("platform", "").lower().strip()
        handle = row.get("handle", "").strip()
        if platform and handle:
            rows.append(row)
    return rows


def normalize_key(value: str) -> str:
    return value.lower().strip().replace(" ", "_").replace("-", "_")


def load_previous_urls(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    urls: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        url = row.get("url")
        if url:
            urls.add(str(url).split("?")[0])
    return urls


def run_json(command: list[str], cwd: str, timeout_seconds: int) -> tuple[list[dict[str, Any]], str | None]:
    try:
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return [], f"timeout after {timeout_seconds}s: {' '.join(command)}"
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        return [], message
    try:
        parsed = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as error:
        return [], f"failed to parse JSON: {error}"
    return parsed if isinstance(parsed, list) else [], None


def compute_age_days(value: Any) -> float | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            published = datetime.strptime(text, fmt)
            return round((datetime.now(timezone.utc) - published).total_seconds() / 86400, 2)
        except ValueError:
            pass
    try:
        published = datetime.fromisoformat(text)
    except ValueError:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - published).total_seconds() / 86400, 2)


def normalize(row: dict[str, Any], account: dict[str, str], platform: str, previous_urls: set[str]) -> dict[str, Any]:
    if platform == "youtube":
        base = row.get("subscribers")
        ratio = row.get("subscriberRatio")
        published_at = row.get("publishedAt")
        title = row.get("title")
    else:
        base = row.get("followers")
        ratio = row.get("viewsPerFollower") or row.get("outlierScore")
        published_at = row.get("postedAt")
        title = row.get("caption") or row.get("title")
    url = row.get("url")
    clean_url = str(url).split("?")[0] if url else ""
    return {
        "platform": platform,
        "source_account": account.get("handle", ""),
        "source_url": account.get("url", ""),
        "query": account.get("query", ""),
        "niche": account.get("niche", ""),
        "priority": account.get("priority", ""),
        "creator": row.get("creator") or row.get("channelTitle") or row.get("channel") or "",
        "base": base,
        "views": row.get("views"),
        "ratio": ratio or row.get("score"),
        "outlier": row.get("outlierScore"),
        "published_at": published_at,
        "age_days": compute_age_days(published_at),
        "title": title or "",
        "url": url,
        "is_new": bool(clean_url and clean_url not in previous_urls),
        "source": row.get("source"),
        "collection_method": "search_seed" if platform in {"youtube", "tiktok"} else "profile",
    }


def within_age(row: dict[str, Any], max_age_days: int) -> bool:
    age_days = row.get("age_days")
    return age_days is None or float(age_days) <= max_age_days


def collect(args: argparse.Namespace, accounts: list[dict[str, str]], previous_urls: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for account in accounts:
        platform = account.get("platform", "").lower()
        handle = account.get("handle", "")
        if args.platform != "all" and platform != args.platform:
            continue
        if platform == "youtube" and args.youtube_bot_dir:
            query = account.get("query") or handle
            command = [
                "node", "src/cli.js", "find", query,
                "--type", "short",
                "--video-duration", "short",
                "--days", str(args.max_age_days),
                "--max-subs", str(args.max_base),
                "--min-views", str(args.min_views),
                "--max-search", "30",
                "--limit", str(args.limit_per_account),
                "--sort", "views",
                "--format", "json",
            ]
            raw, error = run_json(command, args.youtube_bot_dir, args.timeout_seconds)
            errors.extend([f"youtube {handle}: {error}"] if error else [])
            rows.extend(normalize(item, account, platform, previous_urls) for item in raw)
        elif platform == "tiktok" and args.tiktok_bot_dir:
            query = account.get("query") or handle
            command = [
                "node", "src/cli.js", "web-search",
                "--backend", args.tiktok_web_backend,
                "--browser", args.tiktok_web_browser,
                "--headless", args.tiktok_web_headless,
                "--mute-audio", args.tiktok_web_mute_audio,
                query,
                "--max-results", "30",
                "--limit", str(args.limit_per_account),
                "--max-followers", str(args.max_base),
                "--min-views", str(args.min_views),
                "--sort", "views",
                "--format", "json",
            ]
            raw, error = run_json(command, args.tiktok_bot_dir, args.timeout_seconds)
            errors.extend([f"tiktok {handle}: {error}"] if error else [])
            rows.extend(normalize(item, account, platform, previous_urls) for item in raw)
        elif platform == "instagram" and args.ig_bot_dir:
            command = [
                "node", "src/cli.js", "private-profile", handle,
                "--max-results", "20",
                "--limit", str(args.limit_per_account),
                "--min-views", str(args.min_views),
                "--sort", "views-per-follower",
                "--format", "json",
            ]
            raw, error = run_json(command, args.ig_bot_dir, args.timeout_seconds)
            errors.extend([f"instagram {handle}: {error}"] if error else [])
            rows.extend(normalize(item, account, platform, previous_urls) for item in raw)
    for error in errors:
        print(error, file=sys.stderr)
    filtered = [
        row for row in rows
        if int(row.get("views") or 0) >= args.min_views and within_age(row, args.max_age_days)
    ]
    return sorted(filtered, key=lambda row: (int(row.get("views") or 0), float(row.get("ratio") or 0)), reverse=True)


def main() -> int:
    args = parse_args()
    accounts = parse_watchlist(args.watchlist)
    if not accounts:
        print("No watchlist accounts found. Add a markdown table with platform and handle columns.", file=sys.stderr)
        return 2
    previous_urls = load_previous_urls(args.previous)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = collect(args, accounts, previous_urls)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
