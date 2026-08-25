#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check a markdown account watchlist for high-view short-form videos.")
    parser.add_argument("--watchlist", type=Path, required=True, help="Private markdown watchlist path")
    parser.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    parser.add_argument("--health-out", type=Path, help="Optional JSON collector-health receipt")
    parser.add_argument("--previous", type=Path, help="Previous JSONL output for new-link comparison")
    parser.add_argument("--youtube-bot-dir", default=os.environ.get("YOUTUBEBOT_DIR", ""))
    parser.add_argument("--tiktok-bot-dir", default=os.environ.get("TIKTOKBOT_DIR", ""))
    parser.add_argument("--ig-bot-dir", default=os.environ.get("IGBOT_DIR", ""))
    parser.add_argument(
        "--tiktok-collector",
        choices=["profile-feed", "web-search"],
        default="profile-feed",
        help="Use TikTok's anonymous creator embed by default; web-search is an explicit legacy fallback",
    )
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
    parser.add_argument(
        "--failure-threshold",
        type=int,
        default=2,
        help="Stop calling a platform after this many consecutive account failures",
    )
    parser.add_argument(
        "--tiktok-node-fallback",
        choices=["true", "false"],
        default="true",
        help="Retry one failed non-Node TikTok account check with the Node backend",
    )
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


def normalize(
    row: dict[str, Any],
    account: dict[str, str],
    platform: str,
    previous_urls: set[str],
    collection_method: str | None = None,
) -> dict[str, Any]:
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
        "collection_method": collection_method or (
            "search_seed" if platform == "youtube"
            else "profile" if platform in {"tiktok", "instagram"}
            else "unknown"
        ),
    }


def within_age(row: dict[str, Any], max_age_days: int) -> bool:
    age_days = row.get("age_days")
    return age_days is None or float(age_days) <= max_age_days


def empty_health() -> dict[str, dict[str, Any]]:
    return {
        platform: {
            "status": "not_attempted",
            "attempted": 0,
            "succeeded": 0,
            "failed": 0,
            "skipped_after_circuit_breaker": 0,
            "rows_returned": 0,
            "errors": [],
            "fallbacks": [],
        }
        for platform in ("youtube", "tiktok", "instagram")
    }


def finalize_health(health: dict[str, dict[str, Any]]) -> None:
    for platform_health in health.values():
        if platform_health["attempted"] == 0:
            platform_health["status"] = "not_attempted"
        elif platform_health["succeeded"] == 0:
            platform_health["status"] = "unavailable"
        elif platform_health["failed"] or platform_health["skipped_after_circuit_breaker"]:
            platform_health["status"] = "degraded"
        else:
            platform_health["status"] = "success"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def classify_run(
    rows: list[dict[str, Any]],
    health: dict[str, dict[str, Any]],
) -> str:
    attempted = [
        platform_health
        for platform_health in health.values()
        if platform_health["status"] != "not_attempted"
    ]
    if rows:
        return (
            "success"
            if attempted
            and all(item["status"] == "success" for item in attempted)
            else "degraded"
        )
    if any(item["succeeded"] for item in attempted):
        return "empty"
    return "unavailable"


def record_result(
    health: dict[str, dict[str, Any]],
    platform: str,
    raw: list[dict[str, Any]],
    error: str | None,
    label: str,
) -> None:
    platform_health = health[platform]
    platform_health["attempted"] += 1
    if error:
        platform_health["failed"] += 1
        platform_health["errors"].append(f"{label}: {sanitize_error(error)}")
        return
    platform_health["succeeded"] += 1
    platform_health["rows_returned"] += len(raw)


def sanitize_error(error: str, max_length: int = 1200) -> str:
    text = str(error).replace(str(Path.home()), "~")
    text = re.sub(
        r"(['\"]challenge_context['\"]\s*:\s*)['\"][^'\"]+['\"]",
        r"\1'[redacted]'",
        text,
    )
    text = re.sub(
        r"(['\"]challenge_type_enum_str['\"]\s*:\s*)['\"][^'\"]+['\"]",
        r"\1'[redacted]'",
        text,
    )
    if len(text) > max_length:
        return text[:max_length].rstrip() + "…"
    return text


def collect(
    args: argparse.Namespace,
    accounts: list[dict[str, str]],
    previous_urls: set[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    health = empty_health()
    consecutive_failures = {platform: 0 for platform in health}
    for account in accounts:
        platform = account.get("platform", "").lower()
        handle = account.get("handle", "")
        if args.platform != "all" and platform != args.platform:
            continue
        if platform not in health:
            continue
        if consecutive_failures[platform] >= max(args.failure_threshold, 1):
            health[platform]["skipped_after_circuit_breaker"] += 1
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
            record_result(health, platform, raw, error, handle)
            consecutive_failures[platform] = consecutive_failures[platform] + 1 if error else 0
            rows.extend(normalize(item, account, platform, previous_urls) for item in raw)
        elif platform == "tiktok" and args.tiktok_bot_dir:
            if args.tiktok_collector == "profile-feed":
                command = [
                    "node", "src/cli.js", "profile-feed", handle,
                    "--max-results", str(args.limit_per_account),
                    "--limit", str(args.limit_per_account),
                    "--max-followers", str(args.max_base),
                    "--min-views", str(args.min_views),
                    "--sort", "views",
                    "--format", "json",
                ]
            else:
                query = account.get("query") or handle
                command = [
                    "node", "src/cli.js", "web-search",
                    "--enable-browser-adapter",
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
            label = (
                f"{handle} [profile-feed]"
                if args.tiktok_collector == "profile-feed"
                else f"{handle} [{args.tiktok_web_backend}]"
            )
            record_result(health, platform, raw, error, label)
            if (
                error
                and args.tiktok_collector == "web-search"
                and args.tiktok_node_fallback == "true"
                and args.tiktok_web_backend != "node"
            ):
                fallback_command = list(command)
                backend_index = fallback_command.index("--backend") + 1
                fallback_command[backend_index] = "node"
                fallback_raw, fallback_error = run_json(
                    fallback_command,
                    args.tiktok_bot_dir,
                    args.timeout_seconds,
                )
                record_result(health, platform, fallback_raw, fallback_error, f"{handle} [node fallback]")
                health[platform]["fallbacks"].append({
                    "account": handle,
                    "from": args.tiktok_web_backend,
                    "to": "node",
                    "status": "failed" if fallback_error else "success",
                })
                if not fallback_error:
                    raw, error = fallback_raw, None
            consecutive_failures[platform] = consecutive_failures[platform] + 1 if error else 0
            method = "profile" if args.tiktok_collector == "profile-feed" else "search_seed"
            rows.extend(
                normalize(item, account, platform, previous_urls, method)
                for item in raw
            )
        elif platform == "instagram" and args.ig_bot_dir:
            command = [
                "node", "src/cli.js", "private-profile", handle,
                "--enable-unofficial-adapter",
                "--max-results", "20",
                "--limit", str(args.limit_per_account),
                "--min-views", str(args.min_views),
                "--sort", "views-per-follower",
                "--format", "json",
            ]
            raw, error = run_json(command, args.ig_bot_dir, args.timeout_seconds)
            record_result(health, platform, raw, error, handle)
            consecutive_failures[platform] = consecutive_failures[platform] + 1 if error else 0
            rows.extend(normalize(item, account, platform, previous_urls) for item in raw)
    finalize_health(health)
    for platform_health in health.values():
        for error in platform_health["errors"]:
            print(error, file=sys.stderr)
    filtered = [
        row for row in rows
        if int(row.get("views") or 0) >= args.min_views and within_age(row, args.max_age_days)
    ]
    sorted_rows = sorted(
        filtered,
        key=lambda row: (int(row.get("views") or 0), float(row.get("ratio") or 0)),
        reverse=True,
    )
    return sorted_rows, health


def main() -> int:
    args = parse_args()
    accounts = parse_watchlist(args.watchlist)
    if not accounts:
        print("No watchlist accounts found. Add a markdown table with platform and handle columns.", file=sys.stderr)
        return 2
    previous_urls = load_previous_urls(args.previous)
    rows, health = collect(args, accounts, previous_urls)
    generated_at = datetime.now(timezone.utc)
    attempt_path = args.out.with_name(
        f"{args.out.stem}.attempt-"
        f"{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}"
        f"{args.out.suffix}"
    )
    write_jsonl(attempt_path, rows)
    run_status = classify_run(rows, health)
    previous_output_preserved = args.out.exists()
    promoted = bool(rows)
    if promoted:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        os.replace(attempt_path, args.out)
    if args.health_out:
        args.health_out.parent.mkdir(parents=True, exist_ok=True)
        args.health_out.write_text(
            json.dumps({
                "generated_at": generated_at.isoformat(),
                "watchlist": str(args.watchlist),
                "output": str(args.out),
                "attempt_output": str(attempt_path),
                "rows_written": len(rows),
                "run_status": run_status,
                "promoted_to_latest": promoted,
                "previous_output_preserved": (
                    previous_output_preserved and not promoted
                ),
                "platforms": health,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if promoted:
        print(f"promoted {len(rows)} rows to {args.out}")
        return 0
    print(
        f"{run_status}: preserved {args.out}; "
        f"attempt receipt is {attempt_path}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
