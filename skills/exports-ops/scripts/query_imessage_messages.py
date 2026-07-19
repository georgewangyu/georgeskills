#!/usr/bin/env python3
"""Run bounded read-only queries against an iMessage history SQLite index."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def output(payload: object) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise RuntimeError(f"iMessage history index is unavailable: {path}")
    database = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    database.row_factory = sqlite3.Row
    return database


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def bounds(args: argparse.Namespace) -> tuple[int | None, int | None]:
    start = int(parse_date(args.start).timestamp() * 1000) if args.start else None
    end = (
        int((parse_date(args.end) + timedelta(days=1)).timestamp() * 1000)
        if args.end else None
    )
    if start is not None and end is not None and start >= end:
        raise RuntimeError("start must be on or before end")
    return start, end


def fts_expression(value: str) -> str:
    terms = re.findall(r"[^\W_]+", value, flags=re.UNICODE)
    if not terms:
        raise RuntimeError("query contains no searchable words")
    return " AND ".join('"' + term.replace('"', '""') + '"' for term in terms)


def participant_summary(raw: str, preview_limit: int = 5) -> dict[str, object]:
    people = json.loads(raw)
    return {
        "participant_count": len(people),
        "participant_preview": people[:preview_limit],
        "participant_preview_truncated": len(people) > preview_limit,
    }


def bounded_limit(value: str) -> int:
    result = int(value)
    if not 1 <= result <= 100:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return result


def bounded_chars(value: str) -> int:
    result = int(value)
    if not 100 <= result <= 3000:
        raise argparse.ArgumentTypeError("max-chars must be between 100 and 3000")
    return result


def add_filters(
    conditions: list[str], parameters: list[object], args: argparse.Namespace
) -> None:
    start, end = bounds(args)
    if getattr(args, "service", None):
        conditions.append("messages.service = ?")
        parameters.append(args.service)
    if getattr(args, "chat", None):
        conditions.append("LOWER(messages.chat_title) LIKE LOWER(?)")
        parameters.append(f"%{args.chat}%")
    direction = getattr(args, "direction", "any")
    if direction != "any":
        conditions.append("messages.is_from_me = ?")
        parameters.append(1 if direction == "sent" else 0)
    if start is not None:
        conditions.append("messages.timestamp_ms >= ?")
        parameters.append(start)
    if end is not None:
        conditions.append("messages.timestamp_ms < ?")
        parameters.append(end)


def where(conditions: list[str]) -> str:
    return " WHERE " + " AND ".join(conditions) if conditions else ""


def stats(database: sqlite3.Connection, path: Path) -> None:
    metadata = {
        row["key"]: row["value"]
        for row in database.execute("SELECT key, value FROM metadata")
    }
    for key in ("service_counts", "record_counts"):
        metadata[key] = json.loads(metadata[key])
    output({"database": str(path), "metadata": metadata})


def timeline(database: sqlite3.Connection, args: argparse.Namespace) -> None:
    conditions: list[str] = []
    parameters: list[object] = []
    add_filters(conditions, parameters, args)
    width = 4 if args.group == "year" else 7
    sql = f"""
        SELECT substr(timestamp_utc, 1, {width}) AS period,
               service, COUNT(*) AS messages,
               SUM(is_from_me) AS sent_messages,
               COUNT(DISTINCT chat_rowid) AS active_chats
        FROM messages {where(conditions)}
        GROUP BY period, service ORDER BY period, service
    """
    output(
        {
            "group": args.group,
            "date_range": [args.start, args.end],
            "results": [dict(row) for row in database.execute(sql, parameters)],
        }
    )


def chats(database: sqlite3.Connection, args: argparse.Namespace) -> None:
    conditions: list[str] = ["timestamp_ms IS NOT NULL"]
    parameters: list[object] = []
    add_filters(conditions, parameters, args)
    order = {
        "messages": "messages DESC, last_message_utc DESC",
        "span": "span_days DESC, messages DESC",
        "recent": "last_message_utc DESC, messages DESC",
    }[args.sort]
    sql = f"""
        SELECT chat_rowid, MAX(chat_title) AS chat_title,
               MAX(is_group) AS is_group,
               MAX(participants_json) AS participants_json,
               GROUP_CONCAT(DISTINCT service) AS services,
               COUNT(*) AS messages, SUM(is_from_me) AS sent_messages,
               MIN(timestamp_utc) AS first_message_utc,
               MAX(timestamp_utc) AS last_message_utc,
               CAST(julianday(MAX(timestamp_utc)) - julianday(MIN(timestamp_utc))
                    AS INTEGER) AS span_days
        FROM messages {where(conditions)}
        GROUP BY chat_rowid HAVING COUNT(*) >= ?
        ORDER BY {order} LIMIT ?
    """
    parameters.extend([args.min_messages, args.limit])
    results = []
    for row in database.execute(sql, parameters):
        item = dict(row)
        item.update(participant_summary(item.pop("participants_json")))
        item.pop("chat_rowid")
        results.append(item)
    output(
        {
            "sort": args.sort,
            "date_range": [args.start, args.end],
            "results": results,
            "evidence_note": "Chat volume and duration are leads, not measures of closeness.",
        }
    )


def search(database: sqlite3.Connection, args: argparse.Namespace) -> None:
    expression = fts_expression(args.query)
    if args.content_only:
        expression = f"text : ({expression})"
    conditions = ["message_fts MATCH ?"]
    parameters: list[object] = [expression]
    add_filters(conditions, parameters, args)
    order = (
        "rank, messages.timestamp_ms DESC"
        if args.order == "relevance" else "messages.timestamp_ms DESC"
    )
    sql = f"""
        SELECT messages.timestamp_utc, messages.is_from_me, messages.service,
               messages.sender_handle, messages.chat_title,
               messages.participants_json, messages.text, messages.subject,
               messages.message_kind, messages.attachment_count,
               messages.attachment_types, messages.attachment_names,
               messages.associated_message_type,
               messages.associated_message_emoji, messages.date_edited_ms,
               messages.date_retracted_ms, bm25(message_fts) AS rank
        FROM message_fts
        JOIN messages ON messages.id = message_fts.rowid
        {where(conditions)} ORDER BY {order} LIMIT ?
    """
    parameters.append(args.limit)
    results = []
    for row in database.execute(sql, parameters):
        item = dict(row)
        item["direction"] = "sent" if item.pop("is_from_me") else "received"
        item.update(participant_summary(item.pop("participants_json")))
        text = item["text"] or ""
        item["text_truncated"] = len(text) > args.max_chars
        if item["text_truncated"]:
            item["text"] = text[: args.max_chars].rstrip() + "…"
        results.append(item)
    output(
        {
            "query": args.query,
            "search_scope": "content_only" if args.content_only else "all_indexed_fields",
            "date_range": [args.start, args.end],
            "results": results,
            "evidence_note": (
                "Check direction and sender before attribution. "
                + (
                    "Every query term matched the message text field."
                    if args.content_only
                    else "All-fields search can match chat, people, subject, or attachment metadata."
                )
            ),
        }
    )


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--service", choices=["iMessage", "SMS", "RCS"])
    parser.add_argument("--chat", help="Case-insensitive chat-title substring")
    parser.add_argument("--direction", choices=["any", "sent", "received"], default="any")
    parser.add_argument("--start", help="Inclusive UTC date, YYYY-MM-DD")
    parser.add_argument("--end", help="Inclusive UTC date, YYYY-MM-DD")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("stats")

    timeline_parser = subparsers.add_parser("timeline")
    timeline_parser.add_argument("--group", choices=["year", "month"], default="year")
    add_common(timeline_parser)

    chats_parser = subparsers.add_parser("chats")
    add_common(chats_parser)
    chats_parser.add_argument("--sort", choices=["messages", "span", "recent"], default="messages")
    chats_parser.add_argument("--min-messages", type=int, default=1)
    chats_parser.add_argument("--limit", type=bounded_limit, default=20)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--content-only", action="store_true")
    search_parser.add_argument("--order", choices=["relevance", "recent"], default="relevance")
    search_parser.add_argument("--max-chars", type=bounded_chars, default=700)
    search_parser.add_argument("--limit", type=bounded_limit, default=20)
    add_common(search_parser)

    args = parser.parse_args()
    path = args.db.expanduser()
    database = connection(path)
    if args.command == "stats":
        stats(database, path)
    elif args.command == "timeline":
        timeline(database, args)
    elif args.command == "chats":
        chats(database, args)
    elif args.command == "search":
        search(database, args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, sqlite3.Error, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}")
