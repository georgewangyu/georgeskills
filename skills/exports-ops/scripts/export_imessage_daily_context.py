#!/usr/bin/env python3
"""Create a bounded private daily-context extract from macOS Messages."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import OrderedDict
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from index_imessage_messages import (  # noqa: E402
    APPLE_EPOCH,
    SWIFT_DECODER,
    AttributedBodyDecoder,
    apple_time,
    chat_maps,
    message_kind,
)


SCHEMA = "imessage-daily-context-v1"
DEFAULT_SOURCE = Path.home() / "Library" / "Messages" / "chat.db"
AUTOMATED_TEXT_RE = re.compile(
    r"\b(?:verification|security|one[- ]time|login|authentication)\s+code\b|\bOTP\b|\bdo not share\b",
    flags=re.IGNORECASE,
)


def resolve_timezone(timezone_name: str) -> tzinfo:
    """Resolve an IANA timezone or the host's local timezone."""
    if timezone_name != "local":
        return ZoneInfo(timezone_name)

    try:
        resolved_localtime = Path("/etc/localtime").resolve()
        parts = resolved_localtime.parts
        marker_index = parts.index("zoneinfo")
        return ZoneInfo("/".join(parts[marker_index + 1 :]))
    except (OSError, ValueError, ZoneInfoNotFoundError):
        local_timezone = datetime.now().astimezone().tzinfo
        if local_timezone is None:
            raise RuntimeError("unable to resolve the host's local timezone")
        return local_timezone


def consistent_snapshot(source_path: Path, destination_path: Path) -> None:
    """Use SQLite backup semantics so a live WAL database is copied coherently."""
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    destination = sqlite3.connect(destination_path)
    try:
        source.execute("PRAGMA query_only=ON")
        source.backup(destination)
        destination.commit()
        check = destination.execute("PRAGMA quick_check").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"temporary Messages snapshot quick_check failed: {check}")
    finally:
        destination.close()
        source.close()
    os.chmod(destination_path, 0o600)


def apple_storage_uses_nanoseconds(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT MAX(ABS(date)) FROM message WHERE date IS NOT NULL"
    ).fetchone()
    maximum = int(row[0] or 0)
    return maximum > 10_000_000_000


def apple_storage_time(moment: datetime, *, nanoseconds: bool) -> int:
    seconds = (moment.astimezone(timezone.utc) - APPLE_EPOCH).total_seconds()
    return int(seconds * 1_000_000_000) if nanoseconds else int(seconds)


def local_windows(
    day_text: str,
    timezone_name: str,
    *,
    previous_late_hour: int,
) -> tuple[tzinfo, list[dict[str, Any]]]:
    local_timezone = resolve_timezone(timezone_name)
    target_day = date.fromisoformat(day_text)
    target_start = datetime.combine(target_day, time.min, tzinfo=local_timezone)
    target_end = datetime.combine(target_day + timedelta(days=1), time.min, tzinfo=local_timezone)
    previous_late_start = datetime.combine(
        target_day - timedelta(days=1),
        time(previous_late_hour),
        tzinfo=local_timezone,
    )
    return local_timezone, [
        {
            "name": "previous_day_late_window",
            "start_local": previous_late_start,
            "end_local": target_start,
        },
        {
            "name": "target_day",
            "start_local": target_start,
            "end_local": target_end,
        },
    ]


def normalized_text(value: str, max_chars: int) -> tuple[str, bool]:
    cleaned = value.replace("\ufffc", " ").replace("\x00", "")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if len(cleaned) <= max_chars:
        return cleaned, False
    return cleaned[:max_chars].rstrip() + "…", True


def is_short_code(handle: str) -> bool:
    digits = re.sub(r"\D", "", handle)
    return bool(digits) and len(digits) <= 6 and not re.search(r"[A-Za-z]", handle)


def automated_reason(*, service: str, sender_handle: str, text: str, is_from_me: bool) -> str | None:
    if is_from_me or service not in {"SMS", "RCS"}:
        return None
    if is_short_code(sender_handle):
        return "short_code"
    if AUTOMATED_TEXT_RE.search(text):
        return "verification_message"
    return None


def select_rows(
    connection: sqlite3.Connection,
    *,
    start_value: int,
    end_value: int,
    row_limit: int,
) -> list[sqlite3.Row]:
    query = """
        SELECT message.ROWID AS source_rowid, message.guid, message.text,
               message.attributedBody, message.subject, message.service,
               message.date, message.is_from_me, message.item_type,
               message.associated_message_type, handle.id AS sender_handle,
               chat_message_join.chat_id,
               (SELECT COUNT(*) FROM message_attachment_join
                WHERE message_attachment_join.message_id = message.ROWID) AS attachment_count
        FROM message
        LEFT JOIN handle ON handle.ROWID = message.handle_id
        LEFT JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        WHERE message.date >= ? AND message.date < ?
        ORDER BY message.date, message.ROWID
        LIMIT ?
    """
    return list(connection.execute(query, (start_value, end_value, row_limit)))


def unavailable_payload(
    *,
    day_text: str,
    timezone_name: str,
    error: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "unavailable",
        "target_date": day_text,
        "timezone": timezone_name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "error": error,
        "privacy": {
            "contains_message_text": False,
            "attachment_content_loaded": False,
            "journal_contract": "Treat missing context as a source gap; do not query the live database ad hoc.",
        },
        "windows": [],
        "threads": [],
    }


def build_daily_context(
    snapshot_path: Path,
    *,
    day_text: str,
    timezone_name: str,
    previous_late_hour: int = 22,
    max_messages: int = 800,
    max_messages_per_thread: int = 160,
    max_chars_per_message: int = 2000,
    include_automated: bool = False,
    decoder_path: Path = SWIFT_DECODER,
) -> dict[str, Any]:
    local_timezone, windows = local_windows(
        day_text,
        timezone_name,
        previous_late_hour=previous_late_hour,
    )
    connection = sqlite3.connect(f"file:{snapshot_path}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
    if quick_check != "ok":
        connection.close()
        raise RuntimeError(f"Messages snapshot quick_check failed: {quick_check}")

    chats, _ = chat_maps(connection)
    nanoseconds = apple_storage_uses_nanoseconds(connection)
    selected: list[tuple[str, sqlite3.Row]] = []
    raw_query_truncated = False
    per_window_row_limit = max(max_messages * 4, 1000)
    window_receipts: list[dict[str, Any]] = []
    for window in windows:
        rows = select_rows(
            connection,
            start_value=apple_storage_time(window["start_local"], nanoseconds=nanoseconds),
            end_value=apple_storage_time(window["end_local"], nanoseconds=nanoseconds),
            row_limit=per_window_row_limit + 1,
        )
        if len(rows) > per_window_row_limit:
            raw_query_truncated = True
            rows = rows[:per_window_row_limit]
        selected.extend((window["name"], row) for row in rows)
        window_receipts.append(
            {
                "name": window["name"],
                "start_local": window["start_local"].isoformat(),
                "end_local": window["end_local"].isoformat(),
                "raw_rows": len(rows),
            }
        )

    decoder: AttributedBodyDecoder | None = None
    if any(not (row["text"] or "") and row["attributedBody"] is not None for _, row in selected):
        decoder = AttributedBodyDecoder(decoder_path)

    counts = {
        "raw_rows": len(selected),
        "included_messages": 0,
        "automated_filtered": 0,
        "system_or_reaction_filtered": 0,
        "empty_filtered": 0,
        "attributed_decode_failures": 0,
        "global_cap_omitted": 0,
        "per_thread_cap_omitted": 0,
    }
    threads: OrderedDict[tuple[str, int | None], dict[str, Any]] = OrderedDict()
    try:
        for window_name, row in selected:
            if counts["included_messages"] >= max_messages:
                counts["global_cap_omitted"] += 1
                continue

            item_type = int(row["item_type"] or 0)
            associated_type = int(row["associated_message_type"] or 0)
            attachment_count = int(row["attachment_count"] or 0)
            kind = message_kind(item_type, associated_type, attachment_count > 0)
            if kind in {"reaction", "system_or_group_event"}:
                counts["system_or_reaction_filtered"] += 1
                continue

            raw_text = row["text"] or ""
            if not raw_text and row["attributedBody"] is not None and decoder is not None:
                raw_text = decoder.decode(bytes(row["attributedBody"])) or ""
                if not raw_text:
                    counts["attributed_decode_failures"] += 1
            text_value, text_truncated = normalized_text(raw_text, max_chars_per_message)
            if not text_value and not attachment_count:
                counts["empty_filtered"] += 1
                continue

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
            service = row["service"] or chat["service"] or "unknown"
            sender_handle = row["sender_handle"] or ""
            is_from_me = bool(row["is_from_me"])
            automation = automated_reason(
                service=service,
                sender_handle=sender_handle,
                text=text_value,
                is_from_me=is_from_me,
            )
            if automation and not include_automated:
                counts["automated_filtered"] += 1
                continue

            key = (window_name, chat_id)
            if key not in threads:
                people = list(chat["participants"])
                threads[key] = {
                    "window": window_name,
                    "chat_title": chat["title"],
                    "chat_identifier": chat["identifier"],
                    "is_group": bool(chat["is_group"]),
                    "participant_count": len(people),
                    "participant_preview": people[:5],
                    "participant_preview_truncated": len(people) > 5,
                    "services": [],
                    "message_count": 0,
                    "sent_count": 0,
                    "received_count": 0,
                    "omitted_by_thread_cap": 0,
                    "messages": [],
                }
            thread = threads[key]
            if len(thread["messages"]) >= max_messages_per_thread:
                thread["omitted_by_thread_cap"] += 1
                counts["per_thread_cap_omitted"] += 1
                continue

            timestamp_ms, timestamp_utc = apple_time(row["date"])
            timestamp_local = None
            if timestamp_utc:
                timestamp_local = datetime.fromisoformat(timestamp_utc).astimezone(local_timezone).isoformat()
            if service not in thread["services"]:
                thread["services"].append(service)
            thread["message_count"] += 1
            if is_from_me:
                thread["sent_count"] += 1
            else:
                thread["received_count"] += 1
            thread["messages"].append(
                {
                    "timestamp_local": timestamp_local,
                    "timestamp_ms": timestamp_ms,
                    "direction": "sent" if is_from_me else "received",
                    "sender_handle": sender_handle if not is_from_me else "",
                    "service": service,
                    "text": text_value,
                    "text_truncated": text_truncated,
                    "subject": row["subject"] or "",
                    "attachment_count": attachment_count,
                    "attachment_content_loaded": False,
                    "automated_signal": automation,
                }
            )
            counts["included_messages"] += 1
    finally:
        if decoder is not None:
            decoder.close()
        connection.close()

    thread_list = list(threads.values())
    thread_list.sort(
        key=lambda item: (
            item["window"] != "target_day",
            -(item["message_count"]),
            item["chat_title"],
        )
    )
    return {
        "schema": SCHEMA,
        "status": "ready",
        "target_date": day_text,
        "timezone": timezone_name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "method": "temporary_sqlite_backup",
            "live_database_sql_queried_for_message_content": False,
            "snapshot_persisted": False,
            "date_storage": "nanoseconds" if nanoseconds else "seconds",
        },
        "privacy": {
            "contains_message_text": True,
            "attachment_content_loaded": False,
            "automated_messages_excluded": not include_automated,
            "journal_contract": (
                "Use this ignored private staging file for day-level synthesis. "
                "Write derived context to the journal; do not copy raw handles or surprise excerpts."
            ),
        },
        "limits": {
            "max_messages": max_messages,
            "max_messages_per_thread": max_messages_per_thread,
            "max_chars_per_message": max_chars_per_message,
            "raw_query_truncated": raw_query_truncated,
        },
        "counts": counts,
        "windows": window_receipts,
        "threads": thread_list,
    }


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def prune_old_context_files(output_path: Path, *, timezone_name: str, retention_days: int) -> int:
    local_today = datetime.now(resolve_timezone(timezone_name)).date()
    cutoff = local_today - timedelta(days=retention_days)
    removed = 0
    for candidate in output_path.parent.glob("????-??-??.json"):
        try:
            candidate_date = date.fromisoformat(candidate.stem)
        except ValueError:
            continue
        if candidate_date < cutoff and candidate != output_path:
            candidate.unlink()
            removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--timezone", default="local")
    parser.add_argument("--previous-late-hour", type=int, default=22)
    parser.add_argument("--max-messages", type=int, default=800)
    parser.add_argument("--max-messages-per-thread", type=int, default=160)
    parser.add_argument("--max-chars-per-message", type=int, default=2000)
    parser.add_argument("--retention-days", type=int, default=3)
    parser.add_argument("--include-automated", action="store_true")
    parser.add_argument("--decoder", type=Path, default=SWIFT_DECODER)
    parser.add_argument(
        "--soft-fail",
        action="store_true",
        help="Write an unavailable receipt and exit 3 when Messages access is unavailable.",
    )
    args = parser.parse_args()
    if not 0 <= args.previous_late_hour <= 23:
        raise RuntimeError("previous-late-hour must be between 0 and 23")
    if min(args.max_messages, args.max_messages_per_thread, args.max_chars_per_message) < 1:
        raise RuntimeError("message and character limits must be positive")
    if args.retention_days < 0:
        raise RuntimeError("retention-days must be non-negative")

    source_path = args.source.expanduser()
    output_path = args.output.expanduser()
    try:
        with tempfile.TemporaryDirectory(prefix="imessage-daily-context-") as temporary_directory:
            snapshot_path = Path(temporary_directory) / "chat.db"
            consistent_snapshot(source_path, snapshot_path)
            payload = build_daily_context(
                snapshot_path,
                day_text=args.date,
                timezone_name=args.timezone,
                previous_late_hour=args.previous_late_hour,
                max_messages=args.max_messages,
                max_messages_per_thread=args.max_messages_per_thread,
                max_chars_per_message=args.max_chars_per_message,
                include_automated=args.include_automated,
                decoder_path=args.decoder.expanduser(),
            )
    except (
        FileNotFoundError,
        PermissionError,
        RuntimeError,
        sqlite3.Error,
        subprocess.SubprocessError,
        OSError,
    ) as error:
        if not args.soft_fail:
            raise
        payload = unavailable_payload(
            day_text=args.date,
            timezone_name=args.timezone,
            error=f"{type(error).__name__}: {error}",
        )
        write_payload(output_path, payload)
        print(f"iMessage daily context unavailable: {error}")
        print(f"Receipt: {output_path}")
        return 3

    write_payload(output_path, payload)
    removed = prune_old_context_files(
        output_path,
        timezone_name=args.timezone,
        retention_days=args.retention_days,
    )
    counts = payload["counts"]
    print(
        "iMessage daily context ready: "
        f"{counts['included_messages']} message(s) across {len(payload['threads'])} thread-window(s)"
    )
    print(
        "Filtered: "
        f"{counts['automated_filtered']} automated, "
        f"{counts['system_or_reaction_filtered']} system/reaction, "
        f"{counts['empty_filtered']} empty"
    )
    print(f"Private staging file: {output_path}")
    print(f"Old staging files pruned: {removed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        RuntimeError,
        ValueError,
        ZoneInfoNotFoundError,
        sqlite3.Error,
        subprocess.SubprocessError,
        OSError,
    ) as error:
        raise SystemExit(f"error: {error}")
