#!/usr/bin/env python3
"""Run bounded searches against a Google Takeout My Activity index."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--query", help="FTS5 query expression")
    parser.add_argument("--service", help="Optional exact service filter")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    database = args.db.expanduser()
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row

    if args.stats:
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM metadata")
        }
        service_counts = json.loads(metadata["service_counts"])
        services = [
            {"service": service, "records": records}
            for service, records in sorted(
                service_counts.items(), key=lambda item: item[1], reverse=True
            )
        ]
        print(json.dumps({"metadata": metadata, "services": services}, indent=2))
        return 0

    if not args.query:
        parser.error("--query is required unless --stats is used")
    limit = max(1, min(args.limit, 100))

    sql = """
        SELECT
            activities.id,
            activities.service,
            activities.title,
            activities.caption,
            snippet(activity_fts, 2, '[', ']', '…', 24) AS snippet,
            activities.links_json,
            bm25(activity_fts) AS rank
        FROM activity_fts
        JOIN activities ON activities.id = activity_fts.rowid
        WHERE activity_fts MATCH ?
    """
    parameters: list[object] = [args.query]
    if args.service:
        sql += " AND activities.service = ?"
        parameters.append(args.service)
    sql += " ORDER BY rank LIMIT ?"
    parameters.append(limit)

    results = []
    for row in connection.execute(sql, parameters):
        item = dict(row)
        item["links"] = json.loads(item.pop("links_json"))
        results.append(item)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
