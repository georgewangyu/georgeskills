#!/usr/bin/env python3
"""
Incremental X/Twitter import using the bird CLI.

This mirrors the LifeRepo email export model:
- script lives under scripts/exports/
- imported private source data lives under notes-private/
- downstream research/content workflows read exported files
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
SCRIPT_DIR = PRIVATE_REPO_ROOT / "scripts" / "exports" / "social-media"
CONFIG_FILE = SCRIPT_DIR / "config.json"
EXAMPLE_CONFIG_FILE = SCRIPT_DIR / "config.json.example"
X_DIR = PRIVATE_REPO_ROOT / "notes-private" / "social-media" / "x"
STATE_DIR = X_DIR / "state"
DEFAULT_TOKEN_FILE = PRIVATE_REPO_ROOT / ".tokens" / "x-twitter.env"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_slug(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H-%M-%SZ")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {CONFIG_FILE}: {exc}", file=sys.stderr)
        sys.exit(1)


def x_config(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("x")
    return value if isinstance(value, dict) else {}


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        loaded[key] = value
    return loaded


def build_bird_env(cfg: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()

    token_file_value = str(cfg.get("token_file", "")).strip()
    token_file = Path(token_file_value).expanduser() if token_file_value else DEFAULT_TOKEN_FILE
    file_env = load_env_file(token_file)

    # Real environment variables win over the local token file.
    for key, value in file_env.items():
        env.setdefault(key, value)

    return env


def bird_npx_base_command(cfg: dict[str, Any]) -> list[str]:
    npx_path = shutil.which("npx")
    if not npx_path:
        print("Error: npx not found. Install Node.js/npm first.", file=sys.stderr)
        sys.exit(1)

    cmd = [npx_path, "--yes", "@steipete/bird"]
    return cmd


def run_bird_json(cfg: dict[str, Any], args: list[str]) -> Any:
    cmd = bird_npx_base_command(cfg) + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=build_bird_env(cfg))
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "npx bird command failed"
        raise RuntimeError(stderr)
    output = result.stdout.strip()
    if not output:
        return []
    return json.loads(output)


def run_bird_plain(cfg: dict[str, Any], args: list[str]) -> str:
    cmd = bird_npx_base_command(cfg) + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=build_bird_env(cfg))
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "npx bird command failed"
        raise RuntimeError(stderr)
    return result.stdout.strip()


def write_json_outputs(kind: str, payload: Any, ts: datetime) -> Path:
    target_dir = X_DIR / kind
    ensure_dir(target_dir)
    stamped = target_dir / f"{timestamp_slug(ts)}.json"
    latest = target_dir / "latest.json"
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    stamped.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    return stamped


def write_text_output(kind: str, text: str, ts: datetime) -> Path:
    target_dir = X_DIR / kind
    ensure_dir(target_dir)
    stamped = target_dir / f"{timestamp_slug(ts)}.md"
    latest = target_dir / "latest.md"
    rendered = text.rstrip() + "\n"
    stamped.write_text(rendered, encoding="utf-8")
    latest.write_text(rendered, encoding="utf-8")
    return stamped


def save_state(name: str, value: dict[str, Any]) -> None:
    ensure_dir(STATE_DIR)
    path = STATE_DIR / f"{name}.json"
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_state(name: str) -> dict[str, Any]:
    path = STATE_DIR / f"{name}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def normalize_list_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("tweets", "items", "results", "entries", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def tweet_id(item: dict[str, Any]) -> str:
    for key in ("id_str", "rest_id", "id", "tweet_id"):
        value = item.get(key)
        if value is not None:
            return str(value)
    return ""


def author_name(item: dict[str, Any]) -> str:
    author = item.get("author")
    if isinstance(author, dict):
        for key in ("screen_name", "username", "name"):
            value = author.get(key)
            if value:
                return str(value)
    for key in ("screen_name", "username", "user_handle", "handle"):
        value = item.get(key)
        if value:
            return str(value)
    return ""


def tweet_text(item: dict[str, Any]) -> str:
    for key in ("full_text", "text", "content"):
        value = item.get(key)
        if value:
            return str(value).replace("\r\n", "\n").strip()
    legacy = item.get("legacy")
    if isinstance(legacy, dict):
        for key in ("full_text", "text"):
            value = legacy.get(key)
            if value:
                return str(value).replace("\r\n", "\n").strip()
    return ""


def nested_dict(value: Any, *path: str) -> dict[str, Any]:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def article_result(item: dict[str, Any]) -> dict[str, Any]:
    raw = item.get("_raw")
    return nested_dict(raw, "article", "article_results", "result")


def article_plain_text(item: dict[str, Any]) -> str:
    article = item.get("article")
    if isinstance(article, dict):
        value = article.get("plainText")
        if value:
            return str(value).strip()
    raw_article = article_result(item)
    value = raw_article.get("plain_text")
    return str(value).strip() if value else ""


def article_title(item: dict[str, Any]) -> str:
    article = item.get("article")
    if isinstance(article, dict):
        value = article.get("title")
        if value:
            return str(value).strip()
    raw_article = article_result(item)
    value = raw_article.get("title")
    return str(value).strip() if value else ""


def article_url(item: dict[str, Any]) -> str:
    raw = item.get("_raw")
    legacy = nested_dict(raw, "legacy")
    entities = nested_dict(legacy, "entities")
    urls = entities.get("urls")
    if isinstance(urls, list):
        for entry in urls:
            if not isinstance(entry, dict):
                continue
            expanded = entry.get("expanded_url")
            if expanded:
                return str(expanded).strip()
    return ""


def render_article_markdown(item: dict[str, Any]) -> str:
    article = article_result(item)
    content_state = nested_dict(article, "content_state")
    blocks = content_state.get("blocks")
    if not isinstance(blocks, list):
        return article_plain_text(item)

    lines: list[str] = []
    ordered_index = 0

    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text", "")).strip()
        block_type = str(block.get("type", "unstyled"))

        if block_type == "atomic":
            continue

        if not text:
            lines.append("")
            continue

        if block_type == "header-two":
            ordered_index = 0
            lines.extend([f"## {text}", ""])
            continue
        if block_type == "header-three":
            ordered_index = 0
            lines.extend([f"### {text}", ""])
            continue
        if block_type == "unordered-list-item":
            ordered_index = 0
            lines.append(f"- {text}")
            continue
        if block_type == "ordered-list-item":
            ordered_index += 1
            lines.append(f"{ordered_index}. {text}")
            continue

        ordered_index = 0
        lines.extend([text, ""])

    rendered = "\n".join(lines).strip()
    return rendered or article_plain_text(item)


def summarize_detail(item: dict[str, Any], ts: datetime, source: str) -> str:
    identifier = tweet_id(item)
    author = item.get("author") if isinstance(item.get("author"), dict) else {}
    username = str(author.get("username", "")).strip()
    name = str(author.get("name", "")).strip()
    created_at = str(item.get("createdAt", "")).strip()
    like_count = item.get("likeCount")
    reply_count = item.get("replyCount")
    retweet_count = item.get("retweetCount")
    article_name = article_title(item)
    article_body = render_article_markdown(item)
    article_link = article_url(item)
    text = tweet_text(item)

    lines = [
        "# X Post Detail",
        "",
        f"- Captured at: {ts.isoformat()}",
        f"- Source: {source}",
    ]
    if identifier:
        lines.append(f"- Tweet ID: {identifier}")
    if username:
        handle = f"@{username}"
        lines.append(f"- Author: {name} ({handle})" if name else f"- Author: {handle}")
    elif name:
        lines.append(f"- Author: {name}")
    if created_at:
        lines.append(f"- Created at: {created_at}")
    if like_count is not None:
        lines.append(f"- Likes: {like_count}")
    if reply_count is not None:
        lines.append(f"- Replies: {reply_count}")
    if retweet_count is not None:
        lines.append(f"- Reposts: {retweet_count}")
    if article_link:
        lines.append(f"- Article URL: {article_link}")

    lines.extend(["", "## Tweet Text", ""])
    if text:
        lines.append(text)
    else:
        lines.append("_No standalone tweet text extracted._")

    if article_name or article_body:
        lines.extend(["", "## Article Note", ""])
        if article_name:
            lines.extend([f"### {article_name}", ""])
        if article_body:
            lines.append(article_body)
        else:
            lines.append("_Article note metadata present, but body was not extracted._")

    return "\n".join(lines).rstrip() + "\n"


def summarize_items(kind: str, items: list[dict[str, Any]], ts: datetime) -> str:
    lines = [
        f"# X Import Summary - {kind}",
        "",
        f"- Captured at: {ts.isoformat()}",
        f"- Items captured: {len(items)}",
        "",
    ]
    preview_items = items[:15]
    for index, item in enumerate(preview_items, start=1):
        handle = author_name(item)
        text = tweet_text(item)
        text = " ".join(text.split())
        if len(text) > 220:
            text = text[:217] + "..."
        identifier = tweet_id(item)
        label = f"@{handle}" if handle else "(unknown author)"
        suffix = f" [{identifier}]" if identifier else ""
        lines.append(f"{index}. {label}{suffix}")
        if text:
            lines.append(f"   {text}")
    if len(items) > len(preview_items):
        lines.extend(["", f"- Preview truncated to first {len(preview_items)} items."])
    return "\n".join(lines) + "\n"


def export_named_feed(cfg: dict[str, Any], kind: str, args: list[str]) -> tuple[int, Path]:
    ts = now_utc()
    payload = run_bird_json(cfg, args)
    items = normalize_list_payload(payload)
    json_path = write_json_outputs(kind, payload, ts)
    summary = summarize_items(kind, items, ts)
    write_text_output(f"{kind}-summary", summary, ts)
    save_state(f"last_{kind}_export", {"captured_at": ts.isoformat(), "count": len(items), "path": str(json_path)})
    return len(items), json_path


def export_search(cfg: dict[str, Any], query: str, count: int) -> tuple[int, Path]:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in query).strip("-") or "query"
    slug = "-".join(part for part in slug.split("-") if part)[:80]
    kind = f"search/{slug}"
    return export_named_feed(cfg, kind, ["search", query, "--count", str(count), "--json"])


def export_read(cfg: dict[str, Any], source: str) -> tuple[int, Path]:
    ts = now_utc()
    payload = run_bird_json(cfg, ["read", source, "--json-full"])
    item = payload if isinstance(payload, dict) else {}
    identifier = tweet_id(item) or "unknown"
    kind = f"read/{identifier}"
    json_path = write_json_outputs(kind, payload, ts)
    summary = summarize_detail(item, ts, source)
    write_text_output(f"{kind}-summary", summary, ts)
    save_state(
        "last_read_export",
        {
            "captured_at": ts.isoformat(),
            "source": source,
            "tweet_id": identifier,
            "path": str(json_path),
        },
    )
    return 1, json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import X/Twitter data into notes-private using bird.")
    parser.add_argument("--only", choices=["home", "bookmarks", "likes"], help="Export only one feed type.")
    parser.add_argument("--home-count", type=int, help="Override home feed count.")
    parser.add_argument("--bookmarks-count", type=int, help="Override bookmarks count.")
    parser.add_argument("--likes-count", type=int, help="Override likes count.")
    parser.add_argument("--search", help="Optional search query to capture.")
    parser.add_argument("--search-count", type=int, default=20, help="Number of search results to capture.")
    parser.add_argument("--read", help="Fetch one post by tweet ID or URL and store full detail.")
    parser.add_argument("--check-auth", action="store_true", help="Only run bird credential verification.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    cfg = x_config(config)

    if cfg.get("enabled", True) is False:
        print("X export is disabled in config.json", file=sys.stderr)
        return 1

    if args.check_auth:
        try:
            text = run_bird_plain(cfg, ["check", "--plain"])
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(text)
        return 0

    if args.read:
        try:
            _, path = export_read(cfg, args.read)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"read:{args.read} -> {path}")
        return 0

    ensure_dir(X_DIR)
    ensure_dir(STATE_DIR)

    home_count = args.home_count or int(cfg.get("home_count", 40))
    bookmarks_count = args.bookmarks_count or int(cfg.get("bookmarks_count", 40))
    likes_count = args.likes_count or int(cfg.get("likes_count", 20))

    exports: list[str] = []
    failures: list[str] = []

    def record(label: str, fn: Any) -> None:
        try:
            count, path = fn()
            exports.append(f"{label}: {count} items -> {path}")
        except Exception as exc:
            failures.append(f"{label}: {exc}")

    if args.only in (None, "home"):
        record("home", lambda: export_named_feed(cfg, "home", ["home", "--count", str(home_count), "--json"]))
    if args.only in (None, "bookmarks"):
        record(
            "bookmarks",
            lambda: export_named_feed(
                cfg,
                "bookmarks",
                ["bookmarks", "--count", str(bookmarks_count), "--json"],
            ),
        )
    if args.only in (None, "likes"):
        record("likes", lambda: export_named_feed(cfg, "likes", ["likes", "--count", str(likes_count), "--json"]))
    if args.search:
        record(f"search:{args.search}", lambda: export_search(cfg, args.search, args.search_count))

    report_ts = now_utc()
    state = load_state("last_run")
    report_lines = [
        "# X Import Run",
        "",
        f"- Captured at: {report_ts.isoformat()}",
        f"- Previous run: {state.get('captured_at', 'none')}",
        "",
        "## Successful Exports",
        "",
    ]
    if exports:
        report_lines.extend([f"- {line}" for line in exports])
    else:
        report_lines.append("- None")
    report_lines.extend(["", "## Failures", ""])
    if failures:
        report_lines.extend([f"- {line}" for line in failures])
    else:
        report_lines.append("- None")

    write_text_output("summary", "\n".join(report_lines) + "\n", report_ts)
    save_state("last_run", {"captured_at": report_ts.isoformat(), "exports": exports, "failures": failures})

    for line in exports:
        print(line)
    for line in failures:
        print(line, file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
