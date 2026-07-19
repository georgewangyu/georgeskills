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
INDEX_SCRIPT = SKILL_ROOT / "scripts" / "index_imessage_messages.py"
QUERY_SCRIPT = SKILL_ROOT / "scripts" / "query_imessage_messages.py"


def load_index_module():
    spec = importlib.util.spec_from_file_location("index_imessage_messages", INDEX_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def insert_message(connection: sqlite3.Connection, row_id: int, text: str) -> None:
    people = [f"+1555000000{number}" for number in range(8)]
    values = {
        "source_rowid": row_id,
        "guid": f"example-{row_id}",
        "chat_rowid": 1,
        "chat_guid": "example-chat",
        "chat_identifier": "+15550000000",
        "chat_title": "Job pls",
        "is_group": 1,
        "participants_json": json.dumps(people),
        "participants_text": " ".join(people),
        "sender_handle": people[0],
        "is_from_me": int(row_id == 1),
        "service": "iMessage",
        "timestamp_ms": 1_700_000_000_000 + row_id,
        "timestamp_utc": "2023-11-14T22:13:20+00:00",
        "text": text,
        "subject": "",
        "message_kind": "message",
        "item_type": 0,
        "associated_message_type": 0,
        "associated_message_guid": "",
        "associated_message_emoji": "",
        "reply_to_guid": "",
        "attachment_count": 0,
        "attachment_bytes": 0,
        "attachment_types": "",
        "attachment_names": "",
        "attachments_json": "[]",
        "expressive_send_style_id": "",
        "balloon_bundle_id": "",
        "date_edited_ms": None,
        "date_retracted_ms": None,
    }
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f"INSERT INTO messages({columns}) VALUES ({placeholders})",
        tuple(values.values()),
    )


class IMessageMessageIndexTest(unittest.TestCase):
    def test_time_and_snapshot_path_helpers(self) -> None:
        module = load_index_module()
        timestamp_ms, timestamp_utc = module.apple_time(0)
        self.assertEqual(timestamp_ms, 978307200000)
        self.assertEqual(
            datetime.fromisoformat(timestamp_utc),
            datetime(2001, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            module.snapshot_relative(
                "~/Library/Messages/Attachments/aa/bb/example.jpg"
            ),
            "Attachments/aa/bb/example.jpg",
        )

    def test_content_scope_and_participant_preview(self) -> None:
        module = load_index_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "imessage.sqlite"
            with sqlite3.connect(database) as connection:
                module.initialize_database(connection)
                insert_message(connection, 1, "Unrelated lunch plans")
                insert_message(connection, 2, "Career job offer")
                connection.execute("INSERT INTO message_fts(message_fts) VALUES('rebuild')")
                connection.commit()

            all_fields = subprocess.run(
                [
                    sys.executable,
                    str(QUERY_SCRIPT),
                    "--db",
                    str(database),
                    "search",
                    "--query",
                    "job",
                    "--limit",
                    "10",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            all_payload = json.loads(all_fields.stdout)
            self.assertEqual(all_payload["search_scope"], "all_indexed_fields")
            self.assertEqual(len(all_payload["results"]), 2)

            content_only = subprocess.run(
                [
                    sys.executable,
                    str(QUERY_SCRIPT),
                    "--db",
                    str(database),
                    "search",
                    "--query",
                    "job",
                    "--content-only",
                    "--limit",
                    "10",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            content_payload = json.loads(content_only.stdout)
            self.assertEqual(content_payload["search_scope"], "content_only")
            self.assertEqual(len(content_payload["results"]), 1)
            result = content_payload["results"][0]
            self.assertLessEqual(len(result["participant_preview"]), 5)
            self.assertTrue(result["participant_preview_truncated"])
            self.assertNotIn("participants", result)


if __name__ == "__main__":
    unittest.main()
