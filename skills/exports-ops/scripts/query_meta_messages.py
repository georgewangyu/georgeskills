#!/usr/bin/env python3
"""Run bounded read-only queries against a Meta message SQLite index."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def date_bound(value: str) -> int:
    parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def database_stats(connection: sqlite3.Connection) -> dict[str, object]:
    metadata = {
        row["key"]: row["value"]
        for row in connection.execute("SELECT key, value FROM metadata")
    }
    for key in ("source_archives", "platform_counts", "platform_thread_counts"):
        if key in metadata:
            metadata[key] = json.loads(metadata[key])
    platforms = [
        dict(row)
        for row in connection.execute(
            """
            SELECT
                platform,
                COUNT(*) AS records,
                COUNT(DISTINCT thread_path) AS threads,
                MIN(timestamp_utc) AS timestamp_start_utc,
                MAX(timestamp_utc) AS timestamp_end_utc
            FROM messages
            GROUP BY platform
            ORDER BY records DESC
            """
        )
    ]
    return {"metadata": metadata, "platforms": platforms}


def run_query(
    connection: sqlite3.Connection,
    *,
    query: str | None,
    platform: str | None,
    sender: str | None,
    thread: str | None,
    after: str | None,
    before: str | None,
    limit: int,
) -> list[dict[str, object]]:
    select = """
        SELECT
            messages.id,
            messages.platform,
            messages.timestamp_utc,
            messages.sender_name,
            messages.thread_title,
            messages.participants_json,
            messages.attachment_types,
            messages.share_link,
            messages.source_member,
    """
    parameters: list[object] = []
    conditions = []
    if query:
        select += "snippet(message_fts, 4, '[', ']', '…', 24) AS snippet, bm25(message_fts) AS rank"
        source = " FROM message_fts JOIN messages ON messages.id = message_fts.rowid"
        conditions.append("message_fts MATCH ?")
        parameters.append(query)
    else:
        select += "substr(messages.content, 1, 280) AS snippet, NULL AS rank"
        source = " FROM messages"
    if platform:
        conditions.append("messages.platform = ?")
        parameters.append(platform.lower())
    if sender:
        conditions.append("LOWER(messages.sender_name) = LOWER(?)")
        parameters.append(sender)
    if thread:
        conditions.append("LOWER(messages.thread_title) LIKE LOWER(?)")
        parameters.append(f"%{thread}%")
    if after:
        conditions.append("messages.timestamp_ms >= ?")
        parameters.append(date_bound(after))
    if before:
        conditions.append("messages.timestamp_ms < ?")
        parameters.append(date_bound(before))

    sql = select + source
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    if query:
        sql += " ORDER BY rank, messages.timestamp_ms DESC"
    else:
        sql += " ORDER BY messages.timestamp_ms DESC"
    sql += " LIMIT ?"
    parameters.append(max(1, min(limit, 100)))

    results = []
    for row in connection.execute(sql, parameters):
        item = dict(row)
        item["participants"] = json.loads(item.pop("participants_json"))
        results.append(item)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--query", help="Optional FTS5 query expression")
    parser.add_argument("--platform", choices=["facebook", "instagram"])
    parser.add_argument("--sender", help="Optional exact sender name")
    parser.add_argument("--thread", help="Optional thread-title substring")
    parser.add_argument("--after", help="Inclusive UTC date, YYYY-MM-DD")
    parser.add_argument("--before", help="Exclusive UTC date, YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    filters = (args.query, args.platform, args.sender, args.thread, args.after, args.before)
    if not args.stats and not any(filters):
        parser.error("provide --stats or at least one query/filter")

    database = args.db.expanduser()
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    if args.stats:
        output: object = database_stats(connection)
    else:
        output = run_query(
            connection,
            query=args.query,
            platform=args.platform,
            sender=args.sender,
            thread=args.thread,
            after=args.after,
            before=args.before,
            limit=args.limit,
        )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
