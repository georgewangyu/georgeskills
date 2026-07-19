from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "export_imessage_daily_context.py"


def load_module():
    spec = importlib.util.spec_from_file_location("export_imessage_daily_context", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apple_nanoseconds(value: str) -> int:
    apple_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
    moment = datetime.fromisoformat(value).astimezone(timezone.utc)
    return int((moment - apple_epoch).total_seconds() * 1_000_000_000)


def create_messages_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE message (
                guid TEXT, text TEXT, attributedBody BLOB, subject TEXT,
                service TEXT, date INTEGER, is_from_me INTEGER,
                item_type INTEGER, associated_message_type INTEGER,
                handle_id INTEGER
            );
            CREATE TABLE handle (id TEXT);
            CREATE TABLE chat (
                guid TEXT, chat_identifier TEXT, display_name TEXT,
                service_name TEXT, style INTEGER
            );
            CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
            CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
            CREATE TABLE message_attachment_join (message_id INTEGER, attachment_id INTEGER);
            """
        )
        connection.execute("INSERT INTO handle(ROWID, id) VALUES (1, '+15551234567')")
        connection.execute("INSERT INTO handle(ROWID, id) VALUES (2, '54321')")
        connection.execute(
            "INSERT INTO chat(ROWID, guid, chat_identifier, display_name, service_name, style) "
            "VALUES (1, 'chat-one', '+15551234567', 'Friend', 'iMessage', 45)"
        )
        connection.execute(
            "INSERT INTO chat(ROWID, guid, chat_identifier, display_name, service_name, style) "
            "VALUES (2, 'chat-two', '54321', '', 'SMS', 45)"
        )
        connection.execute("INSERT INTO chat_handle_join VALUES (1, 1)")
        connection.execute("INSERT INTO chat_handle_join VALUES (2, 2)")

        messages = [
            (1, "too early", "2026-07-16T21:59:00+00:00", 0, 0, 0, 1, "iMessage"),
            (2, "late decision", "2026-07-16T22:15:00+00:00", 0, 0, 0, 1, "iMessage"),
            (3, "lunch and project plan", "2026-07-17T12:00:00+00:00", 1, 0, 0, 1, "iMessage"),
            (4, "Your verification code is 123456", "2026-07-17T13:00:00+00:00", 0, 0, 0, 2, "SMS"),
            (5, "reaction", "2026-07-17T14:00:00+00:00", 0, 0, 2000, 1, "iMessage"),
            (6, "too late", "2026-07-18T00:00:00+00:00", 0, 0, 0, 1, "iMessage"),
        ]
        for row_id, text, timestamp, is_from_me, item_type, associated_type, handle_id, service in messages:
            connection.execute(
                "INSERT INTO message(ROWID, guid, text, attributedBody, subject, service, date, "
                "is_from_me, item_type, associated_message_type, handle_id) "
                "VALUES (?, ?, ?, NULL, '', ?, ?, ?, ?, ?, ?)",
                (
                    row_id,
                    f"message-{row_id}",
                    text,
                    service,
                    apple_nanoseconds(timestamp),
                    is_from_me,
                    item_type,
                    associated_type,
                    handle_id,
                ),
            )
            connection.execute(
                "INSERT INTO chat_message_join(chat_id, message_id) VALUES (?, ?)",
                (2 if handle_id == 2 else 1, row_id),
            )
        connection.commit()


class IMessageDailyContextTest(unittest.TestCase):
    def test_local_timezone_resolves(self) -> None:
        module_spec = importlib.util.spec_from_file_location("imessage_daily_context", SCRIPT)
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        self.assertIsNotNone(module.resolve_timezone("local"))

    def test_consistent_snapshot_and_bounded_day_extract(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.db"
            snapshot = root / "snapshot.db"
            create_messages_database(source)

            module.consistent_snapshot(source, snapshot)
            payload = module.build_daily_context(
                snapshot,
                day_text="2026-07-17",
                timezone_name="UTC",
            )

            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["counts"]["included_messages"], 2)
            self.assertEqual(payload["counts"]["automated_filtered"], 1)
            self.assertEqual(payload["counts"]["system_or_reaction_filtered"], 1)
            self.assertFalse(payload["source"]["snapshot_persisted"])
            self.assertFalse(payload["privacy"]["attachment_content_loaded"])
            messages = [
                message
                for thread in payload["threads"]
                for message in thread["messages"]
            ]
            self.assertEqual(
                {message["text"] for message in messages},
                {"late decision", "lunch and project plan"},
            )
            self.assertTrue(all(not message["attachment_content_loaded"] for message in messages))

    def test_soft_fail_writes_bounded_unavailable_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "context.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source",
                    str(root / "missing-chat.db"),
                    "--output",
                    str(output),
                    "--date",
                    "2026-07-17",
                    "--timezone",
                    "UTC",
                    "--soft-fail",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 3)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "unavailable")
            self.assertFalse(payload["privacy"]["contains_message_text"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
