#!/usr/bin/env python3
"""Build a searchable SQLite index from Google Takeout My Activity HTML."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable


SPACE = re.compile(r"\s+")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def normalize(parts: list[str]) -> str:
    return SPACE.sub(" ", " ".join(parts)).strip()


class ActivityParser(HTMLParser):
    def __init__(self, emit: Callable[[dict[str, Any]], None]):
        super().__init__(convert_charrefs=True)
        self.emit = emit
        self.stack: list[tuple[str, set[str]]] = []
        self.record: dict[str, Any] | None = None
        self.outer_depth = 0
        self.skip_depth = 0
        self.title_depth = 0
        self.caption_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if "mdl-typography--title" in classes:
            self.title_depth += 1
        if "mdl-typography--caption" in classes:
            self.caption_depth += 1

        if "outer-cell" in classes and self.record is None:
            self.record = {
                "title": [],
                "body": [],
                "caption": [],
                "links": [],
            }
            self.outer_depth = 1
        elif self.record is not None and tag == "div":
            self.outer_depth += 1

        if tag not in VOID_TAGS:
            self.stack.append((tag, classes))
        if self.record is not None and tag == "a" and attr_map.get("href"):
            self.record["links"].append(attr_map["href"])

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.record is not None and tag == "div":
            self.outer_depth -= 1
            if self.outer_depth == 0:
                completed = self.record
                self.record = None
                self.emit(
                    {
                        "title": normalize(completed["title"]),
                        "body": normalize(completed["body"]),
                        "caption": normalize(completed["caption"]),
                        "links": list(dict.fromkeys(completed["links"])),
                    }
                )
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if self.stack:
            _, classes = self.stack.pop()
            if "mdl-typography--title" in classes:
                self.title_depth -= 1
            if "mdl-typography--caption" in classes:
                self.caption_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.record is None or self.skip_depth or not data.strip():
            return
        if self.title_depth:
            self.record["title"].append(data)
        elif self.caption_depth:
            self.record["caption"].append(data)
        else:
            self.record["body"].append(data)


def service_from_member(member: str) -> str:
    parts = member.replace("\\", "/").split("/")
    return parts[2] if len(parts) > 3 else "Unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_zip = args.zip.expanduser()
    output = args.output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)

    connection = sqlite3.connect(temporary)
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE activities (
            id INTEGER PRIMARY KEY,
            service TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            caption TEXT NOT NULL,
            links_json TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_sequence INTEGER NOT NULL,
            UNIQUE(source_member, source_sequence)
        );
        CREATE INDEX activities_service_idx ON activities(service);
        CREATE VIRTUAL TABLE activity_fts USING fts5(
            service, title, body, caption,
            content='activities', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        """
    )

    counts: Counter[str] = Counter()
    with zipfile.ZipFile(source_zip) as package:
        members = sorted(
            info.filename
            for info in package.infolist()
            if info.filename.startswith("Takeout/My Activity/")
            and info.filename.endswith("/MyActivity.html")
        )
        for index, member in enumerate(members, start=1):
            service = service_from_member(member)
            sequence = 0

            def emit(record: dict[str, Any]) -> None:
                nonlocal sequence
                sequence += 1
                connection.execute(
                    """
                    INSERT INTO activities(
                        service, title, body, caption, links_json,
                        source_member, source_sequence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        service,
                        record["title"],
                        record["body"],
                        record["caption"],
                        json.dumps(record["links"], ensure_ascii=False),
                        member,
                        sequence,
                    ),
                )

            activity_parser = ActivityParser(emit)
            with package.open(member) as source:
                while chunk := source.read(1024 * 1024):
                    activity_parser.feed(chunk.decode("utf-8", errors="replace"))
            activity_parser.close()
            counts[service] = sequence
            connection.commit()
            print(
                f"[{index}/{len(members)}] {service}: {sequence:,} records",
                flush=True,
            )

    connection.execute(
        "INSERT INTO activity_fts(activity_fts) VALUES('rebuild')"
    )
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        [
            ("schema", "google-takeout-my-activity-index-v1"),
            ("source_zip", str(source_zip)),
            ("total_records", str(sum(counts.values()))),
            ("service_counts", json.dumps(dict(sorted(counts.items())))),
        ],
    )
    connection.commit()
    check = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {check}")
    fts_check = connection.execute(
        "INSERT INTO activity_fts(activity_fts, rank) VALUES('integrity-check', 1)"
    )
    list(fts_check)
    connection.close()
    os.replace(temporary, output)

    print(f"Indexed {sum(counts.values()):,} records across {len(counts)} services")
    print(f"Output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
