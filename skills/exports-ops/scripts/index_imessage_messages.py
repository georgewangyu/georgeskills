#!/usr/bin/env python3
"""Build an atomic SQLite/FTS5 index from a read-only macOS Messages snapshot."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sqlite3
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
SCRIPT_DIR = Path(__file__).resolve().parent
SWIFT_DECODER = SCRIPT_DIR / "decode_imessage_attributed.swift"


def apple_time(value: int | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, None
    seconds = value / 1_000_000_000 if abs(value) > 10_000_000_000 else value
    moment = APPLE_EPOCH + timedelta(seconds=seconds)
    return int(moment.timestamp() * 1000), moment.isoformat()


def snapshot_relative(filename: str | None) -> str:
    if not filename:
        return ""
    expanded = os.path.expanduser(filename)
    marker = f"{os.sep}Library{os.sep}Messages{os.sep}"
    if marker in expanded:
        return expanded.split(marker, 1)[1]
    return Path(expanded).name


class AttributedBodyDecoder:
    def __init__(self, source: Path) -> None:
        if not source.is_file():
            raise RuntimeError(f"Swift attributed-body decoder is missing: {source}")
        self._temporary = tempfile.TemporaryDirectory(prefix="imessage-decoder-")
        binary = Path(self._temporary.name) / "decode-imessage-attributed"
        subprocess.run(
            ["xcrun", "swiftc", str(source), "-o", str(binary)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._binary = binary
        self._process = self._launch()

    def _launch(self) -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            [str(self._binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def _restart(self) -> None:
        if self._process.poll() is None:
            self._process.kill()
        self._process.wait()
        self._process = self._launch()

    def decode(self, payload: bytes) -> str | None:
        if self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("attributed-body decoder pipes are unavailable")
        try:
            self._process.stdin.write(base64.b64encode(payload) + b"\n")
            self._process.stdin.flush()
        except BrokenPipeError:
            self._restart()
            return None
        line = self._process.stdout.readline().strip()
        if not line:
            self._restart()
            return None
        if line.startswith(b"!"):
            return None
        return base64.b64decode(line).decode("utf-8")

    def close(self) -> None:
        if self._process.poll() is None:
            if self._process.stdin is not None:
                try:
                    self._process.stdin.close()
                except BrokenPipeError:
                    pass
            try:
                self._process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        self._temporary.cleanup()

    def __enter__(self) -> "AttributedBodyDecoder":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def source_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    database = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    database.row_factory = sqlite3.Row
    return database


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            source_rowid INTEGER NOT NULL UNIQUE,
            guid TEXT NOT NULL,
            chat_rowid INTEGER,
            chat_guid TEXT NOT NULL,
            chat_identifier TEXT NOT NULL,
            chat_title TEXT NOT NULL,
            is_group INTEGER NOT NULL,
            participants_json TEXT NOT NULL,
            participants_text TEXT NOT NULL,
            sender_handle TEXT NOT NULL,
            is_from_me INTEGER NOT NULL,
            service TEXT NOT NULL,
            timestamp_ms INTEGER,
            timestamp_utc TEXT,
            text TEXT NOT NULL,
            subject TEXT NOT NULL,
            message_kind TEXT NOT NULL,
            item_type INTEGER NOT NULL,
            associated_message_type INTEGER NOT NULL,
            associated_message_guid TEXT NOT NULL,
            associated_message_emoji TEXT NOT NULL,
            reply_to_guid TEXT NOT NULL,
            attachment_count INTEGER NOT NULL,
            attachment_bytes INTEGER NOT NULL,
            attachment_types TEXT NOT NULL,
            attachment_names TEXT NOT NULL,
            attachments_json TEXT NOT NULL,
            expressive_send_style_id TEXT NOT NULL,
            balloon_bundle_id TEXT NOT NULL,
            date_edited_ms INTEGER,
            date_retracted_ms INTEGER
        );
        CREATE INDEX messages_timestamp_idx ON messages(timestamp_ms);
        CREATE INDEX messages_chat_idx ON messages(chat_rowid, timestamp_ms);
        CREATE INDEX messages_sender_idx ON messages(sender_handle, timestamp_ms);
        CREATE INDEX messages_direction_idx ON messages(is_from_me, timestamp_ms);
        CREATE INDEX messages_service_idx ON messages(service, timestamp_ms);
        CREATE VIRTUAL TABLE message_fts USING fts5(
            chat_title,
            chat_identifier,
            participants_text,
            sender_handle,
            text,
            subject,
            attachment_types,
            attachment_names,
            content='messages',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        """
    )


def chat_maps(source: sqlite3.Connection) -> tuple[dict[int, dict[str, Any]], int]:
    participants: dict[int, list[str]] = defaultdict(list)
    for row in source.execute(
        """
        SELECT chat_handle_join.chat_id, handle.id
        FROM chat_handle_join
        JOIN handle ON handle.ROWID = chat_handle_join.handle_id
        ORDER BY chat_handle_join.chat_id, handle.id
        """
    ):
        if row["id"] and row["id"] not in participants[row["chat_id"]]:
            participants[row["chat_id"]].append(row["id"])

    chats: dict[int, dict[str, Any]] = {}
    for row in source.execute(
        """
        SELECT ROWID, guid, chat_identifier, display_name, service_name, style
        FROM chat
        """
    ):
        chat_id = row["ROWID"]
        people = participants.get(chat_id, [])
        is_group = int(row["style"] == 43 or len(people) > 1)
        title = row["display_name"] or ""
        if not title:
            if is_group:
                preview = ", ".join(people[:6])
                title = f"Group: {preview}" + ("…" if len(people) > 6 else "")
            else:
                title = row["chat_identifier"] or (people[0] if people else "Unknown chat")
        chats[chat_id] = {
            "guid": row["guid"] or "",
            "identifier": row["chat_identifier"] or "",
            "title": title,
            "service": row["service_name"] or "",
            "is_group": is_group,
            "participants": people,
        }
    return chats, len(chats)


def attachment_map(source: sqlite3.Connection) -> dict[int, list[dict[str, Any]]]:
    attachments: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in source.execute(
        """
        SELECT message_attachment_join.message_id, attachment.guid,
               attachment.filename, attachment.transfer_name,
               attachment.mime_type, attachment.uti, attachment.total_bytes,
               attachment.is_sticker
        FROM message_attachment_join
        JOIN attachment ON attachment.ROWID = message_attachment_join.attachment_id
        ORDER BY message_attachment_join.message_id, attachment.ROWID
        """
    ):
        attachments[row["message_id"]].append(
            {
                "guid": row["guid"] or "",
                "relative_path": snapshot_relative(row["filename"]),
                "name": row["transfer_name"] or "",
                "mime_type": row["mime_type"] or "",
                "uti": row["uti"] or "",
                "bytes": int(row["total_bytes"] or 0),
                "is_sticker": bool(row["is_sticker"]),
            }
        )
    return attachments


def message_kind(item_type: int, associated_type: int, has_attachments: bool) -> str:
    if associated_type:
        return "reaction"
    if item_type:
        return "system_or_group_event"
    if has_attachments:
        return "message_with_attachment"
    return "message"


def build_index(source_path: Path, output_path: Path, decoder_path: Path) -> dict[str, Any]:
    source = source_connection(source_path)
    quick_check = source.execute("PRAGMA quick_check").fetchone()[0]
    if quick_check != "ok":
        raise RuntimeError(f"source SQLite quick_check failed: {quick_check}")

    chats, chat_count = chat_maps(source)
    attachments = attachment_map(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    output = sqlite3.connect(temporary)
    initialize_database(output)

    counts: Counter[str] = Counter()
    service_counts: Counter[str] = Counter()
    start_ms: int | None = None
    end_ms: int | None = None
    insert_sql = """
        INSERT INTO messages(
            source_rowid, guid, chat_rowid, chat_guid, chat_identifier,
            chat_title, is_group, participants_json, participants_text,
            sender_handle, is_from_me, service, timestamp_ms, timestamp_utc,
            text, subject, message_kind, item_type, associated_message_type,
            associated_message_guid, associated_message_emoji, reply_to_guid,
            attachment_count, attachment_bytes, attachment_types,
            attachment_names, attachments_json, expressive_send_style_id,
            balloon_bundle_id, date_edited_ms, date_retracted_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    query = """
        SELECT message.ROWID AS source_rowid, message.guid, message.text,
               message.attributedBody, message.subject, message.service,
               message.date, message.is_from_me, message.item_type,
               message.associated_message_type, message.associated_message_guid,
               message.associated_message_emoji, message.reply_to_guid,
               message.expressive_send_style_id, message.balloon_bundle_id,
               message.date_edited, message.date_retracted,
               handle.id AS sender_handle, chat_message_join.chat_id
        FROM message
        LEFT JOIN handle ON handle.ROWID = message.handle_id
        LEFT JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        ORDER BY message.ROWID
    """

    with AttributedBodyDecoder(decoder_path) as decoder:
        for index, row in enumerate(source.execute(query), start=1):
            raw_text = row["text"] or ""
            if raw_text:
                counts["plain_text_records"] += 1
            elif row["attributedBody"] is not None:
                decoded = decoder.decode(row["attributedBody"])
                if decoded is None:
                    counts["attributed_decode_failures"] += 1
                else:
                    raw_text = decoded
                    counts["attributed_text_records"] += 1
            if not raw_text:
                counts["empty_text_records"] += 1

            chat_id = row["chat_id"]
            chat = chats.get(
                chat_id,
                {
                    "guid": "",
                    "identifier": "",
                    "title": "Unlinked message",
                    "service": "",
                    "is_group": 0,
                    "participants": [],
                },
            )
            message_attachments = attachments.get(row["source_rowid"], [])
            attachment_types = sorted(
                {
                    item["mime_type"] or item["uti"] or "attachment"
                    for item in message_attachments
                }
            )
            attachment_names = [
                item["name"] or Path(item["relative_path"]).name
                for item in message_attachments
                if item["name"] or item["relative_path"]
            ]
            timestamp_ms, timestamp_utc = apple_time(row["date"])
            edited_ms, _ = apple_time(row["date_edited"])
            retracted_ms, _ = apple_time(row["date_retracted"])
            if timestamp_ms is not None:
                start_ms = timestamp_ms if start_ms is None else min(start_ms, timestamp_ms)
                end_ms = timestamp_ms if end_ms is None else max(end_ms, timestamp_ms)
            service = row["service"] or chat["service"] or "unknown"
            service_counts[service] += 1
            counts["from_me" if row["is_from_me"] else "to_me"] += 1
            if message_attachments:
                counts["messages_with_attachments"] += 1

            item_type = int(row["item_type"] or 0)
            associated_type = int(row["associated_message_type"] or 0)
            kind = message_kind(item_type, associated_type, bool(message_attachments))
            counts[f"kind:{kind}"] += 1
            output.execute(
                insert_sql,
                (
                    row["source_rowid"], row["guid"], chat_id, chat["guid"],
                    chat["identifier"], chat["title"], chat["is_group"],
                    json.dumps(chat["participants"], ensure_ascii=False),
                    " ".join(chat["participants"]), row["sender_handle"] or "",
                    int(row["is_from_me"] or 0), service, timestamp_ms, timestamp_utc,
                    raw_text, row["subject"] or "", kind, item_type, associated_type,
                    row["associated_message_guid"] or "",
                    row["associated_message_emoji"] or "", row["reply_to_guid"] or "",
                    len(message_attachments),
                    sum(int(item["bytes"]) for item in message_attachments),
                    ",".join(attachment_types), " ".join(attachment_names),
                    json.dumps(message_attachments, ensure_ascii=False),
                    row["expressive_send_style_id"] or "",
                    row["balloon_bundle_id"] or "", edited_ms, retracted_ms,
                ),
            )
            counts["total_records"] += 1
            if index % 5000 == 0:
                output.commit()
                print(f"Indexed {index:,} messages", flush=True)

    output.commit()
    output.execute("INSERT INTO message_fts(message_fts) VALUES('rebuild')")
    metadata = {
        "schema": "imessage-history-index-v1",
        "source_database": str(source_path),
        "total_records": str(counts["total_records"]),
        "chat_count": str(chat_count),
        "service_counts": json.dumps(dict(sorted(service_counts.items()))),
        "record_counts": json.dumps(dict(sorted(counts.items()))),
        "timestamp_start_utc": (
            datetime.fromtimestamp(start_ms / 1000, timezone.utc).isoformat()
            if start_ms is not None else ""
        ),
        "timestamp_end_utc": (
            datetime.fromtimestamp(end_ms / 1000, timezone.utc).isoformat()
            if end_ms is not None else ""
        ),
    }
    output.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())
    output.commit()
    check = output.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"output SQLite integrity_check failed: {check}")
    list(
        output.execute(
            "INSERT INTO message_fts(message_fts, rank) VALUES('integrity-check', 1)"
        )
    )
    output.close()
    source.close()
    os.replace(temporary, output_path)
    print(f"Indexed {counts['total_records']:,} Messages records")
    print(f"Output: {output_path}")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Snapshot chat.db")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--decoder", type=Path, default=SWIFT_DECODER)
    args = parser.parse_args()
    build_index(args.source.expanduser(), args.output.expanduser(), args.decoder.expanduser())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, sqlite3.Error, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"error: {error}")
