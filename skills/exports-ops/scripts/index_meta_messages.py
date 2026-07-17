#!/usr/bin/env python3
"""Build a searchable SQLite index from Meta Facebook and Instagram exports."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MESSAGE_PREFIXES = {
    "facebook": "your_facebook_activity/messages/",
    "instagram": "your_instagram_activity/messages/",
}
ATTACHMENT_KEYS = (
    "photos",
    "videos",
    "audio_files",
    "gifs",
    "files",
    "sticker",
    "share",
)
MOJIBAKE_MARKERS = "ÃÂâð"


def mojibake_score(value: str) -> int:
    controls = sum("\u0080" <= character <= "\u009f" for character in value)
    markers = sum(value.count(character) for character in MOJIBAKE_MARKERS)
    return controls * 3 + markers


def decode_meta_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text or mojibake_score(text) == 0:
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return repaired if mojibake_score(repaired) < mojibake_score(text) else text


def parse_archive(value: str) -> tuple[str, Path]:
    try:
        platform, raw_path = value.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use PLATFORM=ZIP") from exc
    platform = platform.strip().lower()
    if platform not in MESSAGE_PREFIXES:
        choices = ", ".join(sorted(MESSAGE_PREFIXES))
        raise argparse.ArgumentTypeError(f"platform must be one of: {choices}")
    path = Path(raw_path).expanduser()
    return platform, path


def message_members(package: zipfile.ZipFile, platform: str) -> list[str]:
    prefix = MESSAGE_PREFIXES[platform]
    return sorted(
        info.filename
        for info in package.infolist()
        if info.filename.startswith(prefix)
        and "/message_" in info.filename
        and info.filename.endswith(".json")
    )


def participant_names(payload: dict[str, Any]) -> list[str]:
    names = []
    for participant in payload.get("participants", []):
        name = decode_meta_text(participant.get("name"))
        if name and name not in names:
            names.append(name)
    return names


def attachment_types(message: dict[str, Any]) -> str:
    return ",".join(key for key in ATTACHMENT_KEYS if message.get(key))


def share_link(message: dict[str, Any]) -> str:
    share = message.get("share")
    if not isinstance(share, dict):
        return ""
    return decode_meta_text(share.get("link"))


def normalized_reactions(message: dict[str, Any]) -> str:
    reactions = []
    for reaction in message.get("reactions", []):
        if not isinstance(reaction, dict):
            continue
        reactions.append(
            {
                "reaction": decode_meta_text(reaction.get("reaction")),
                "actor": decode_meta_text(reaction.get("actor")),
            }
        )
    return json.dumps(reactions, ensure_ascii=False)


def utc_timestamp(timestamp_ms: int | None) -> str | None:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat()


def iter_messages(
    archive: Path, platform: str
) -> Iterable[tuple[str, int, dict[str, Any], dict[str, Any]]]:
    with zipfile.ZipFile(archive) as package:
        for member in message_members(package, platform):
            payload = json.loads(package.read(member))
            for sequence, message in enumerate(payload.get("messages", []), start=1):
                yield member, sequence, payload, message


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            platform TEXT NOT NULL,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_sequence INTEGER NOT NULL,
            thread_path TEXT NOT NULL,
            thread_title TEXT NOT NULL,
            participants_json TEXT NOT NULL,
            participants_text TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            timestamp_ms INTEGER,
            timestamp_utc TEXT,
            content TEXT NOT NULL,
            attachment_types TEXT NOT NULL,
            share_link TEXT NOT NULL,
            reactions_json TEXT NOT NULL,
            UNIQUE(platform, source_member, source_sequence)
        );
        CREATE INDEX messages_platform_idx ON messages(platform);
        CREATE INDEX messages_timestamp_idx ON messages(timestamp_ms);
        CREATE INDEX messages_thread_idx ON messages(platform, thread_path);
        CREATE INDEX messages_sender_idx ON messages(platform, sender_name);
        CREATE VIRTUAL TABLE message_fts USING fts5(
            platform,
            thread_title,
            participants_text,
            sender_name,
            content,
            attachment_types,
            share_link,
            content='messages',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        """
    )


def build_index(archives: list[tuple[str, Path]], output: Path) -> dict[str, Any]:
    if not archives:
        raise ValueError("at least one archive is required")
    for _, archive in archives:
        if not archive.is_file():
            raise FileNotFoundError(archive)

    output = output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)

    connection = sqlite3.connect(temporary)
    initialize_database(connection)
    counts: Counter[str] = Counter()
    thread_paths: dict[str, set[str]] = {
        platform: set() for platform in MESSAGE_PREFIXES
    }
    duplicate_records = 0
    timestamp_start: int | None = None
    timestamp_end: int | None = None

    for archive_index, (platform, archive) in enumerate(archives, start=1):
        archive_inserted = 0
        for member, sequence, payload, message in iter_messages(archive, platform):
            participants = participant_names(payload)
            timestamp_value = message.get("timestamp_ms")
            timestamp_ms = (
                int(timestamp_value)
                if isinstance(timestamp_value, (int, float))
                else None
            )
            before = connection.total_changes
            connection.execute(
                """
                INSERT OR IGNORE INTO messages(
                    platform,
                    source_archive,
                    source_member,
                    source_sequence,
                    thread_path,
                    thread_title,
                    participants_json,
                    participants_text,
                    sender_name,
                    timestamp_ms,
                    timestamp_utc,
                    content,
                    attachment_types,
                    share_link,
                    reactions_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    platform,
                    archive.name,
                    member,
                    sequence,
                    decode_meta_text(payload.get("thread_path")) or member.rsplit("/", 1)[0],
                    decode_meta_text(payload.get("title")),
                    json.dumps(participants, ensure_ascii=False),
                    " ".join(participants),
                    decode_meta_text(message.get("sender_name")),
                    timestamp_ms,
                    utc_timestamp(timestamp_ms),
                    decode_meta_text(message.get("content")),
                    attachment_types(message),
                    share_link(message),
                    normalized_reactions(message),
                ),
            )
            if connection.total_changes == before:
                duplicate_records += 1
                continue
            archive_inserted += 1
            counts[platform] += 1
            thread_paths[platform].add(member.rsplit("/", 1)[0])
            if timestamp_ms is not None:
                timestamp_start = (
                    timestamp_ms
                    if timestamp_start is None
                    else min(timestamp_start, timestamp_ms)
                )
                timestamp_end = (
                    timestamp_ms
                    if timestamp_end is None
                    else max(timestamp_end, timestamp_ms)
                )
        connection.commit()
        print(
            f"[{archive_index}/{len(archives)}] {platform} {archive.name}: "
            f"{archive_inserted:,} records",
            flush=True,
        )

    connection.execute("INSERT INTO message_fts(message_fts) VALUES('rebuild')")
    metadata = {
        "schema": "meta-message-index-v1",
        "source_archives": json.dumps(
            [
                {"platform": platform, "path": str(archive)}
                for platform, archive in archives
            ]
        ),
        "total_records": str(sum(counts.values())),
        "platform_counts": json.dumps(dict(sorted(counts.items()))),
        "platform_thread_counts": json.dumps(
            {
                platform: len(paths)
                for platform, paths in sorted(thread_paths.items())
                if paths
            }
        ),
        "duplicate_records_ignored": str(duplicate_records),
        "timestamp_start_utc": utc_timestamp(timestamp_start) or "",
        "timestamp_end_utc": utc_timestamp(timestamp_end) or "",
    }
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items()
    )
    connection.commit()
    check = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {check}")
    list(
        connection.execute(
            "INSERT INTO message_fts(message_fts, rank) "
            "VALUES('integrity-check', 1)"
        )
    )
    connection.close()
    os.replace(temporary, output)

    print(
        f"Indexed {sum(counts.values()):,} records across "
        f"{len([value for value in counts.values() if value])} platforms"
    )
    print(f"Output: {output}")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        action="append",
        type=parse_archive,
        required=True,
        metavar="PLATFORM=ZIP",
        help="Repeat for every archive part in one Meta export snapshot.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_index(args.archive, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
