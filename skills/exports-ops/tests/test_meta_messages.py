from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
INDEX_SCRIPT = SKILL_ROOT / "scripts" / "index_meta_messages.py"
QUERY_SCRIPT = SKILL_ROOT / "scripts" / "query_meta_messages.py"


def write_archive(path: Path, platform: str, content: str) -> None:
    prefix = {
        "facebook": "your_facebook_activity/messages",
        "instagram": "your_instagram_activity/messages",
    }[platform]
    payload = {
        "participants": [{"name": "Example User"}, {"name": "Friend"}],
        "messages": [
            {
                "sender_name": "Example User",
                "timestamp_ms": 1577836800000,
                "content": content,
                "reactions": [{"reaction": "\u00e2\u009d\u00a4", "actor": "Friend"}],
            }
        ],
        "title": f"{platform.title()} Test Thread",
        "thread_path": f"{prefix}/inbox/test_thread_1",
    }
    member = f"{prefix}/inbox/test_thread_1/message_1.json"
    with zipfile.ZipFile(path, "w") as package:
        package.writestr(member, json.dumps(payload))


class MetaMessageIndexTest(unittest.TestCase):
    def test_index_query_and_duplicate_suppression(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            facebook = root / "facebook.zip"
            facebook_duplicate = root / "facebook-duplicate.zip"
            instagram = root / "instagram.zip"
            database = root / "meta.sqlite"
            write_archive(facebook, "facebook", "It\u00e2\u0080\u0099s caf\u00c3\u00a9 time")
            write_archive(
                facebook_duplicate,
                "facebook",
                "It\u00e2\u0080\u0099s caf\u00c3\u00a9 time",
            )
            write_archive(instagram, "instagram", "Instagram hello")

            subprocess.run(
                [
                    sys.executable,
                    str(INDEX_SCRIPT),
                    "--archive",
                    f"facebook={facebook}",
                    "--archive",
                    f"facebook={facebook_duplicate}",
                    "--archive",
                    f"instagram={instagram}",
                    "--output",
                    str(database),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                    2,
                )
                repaired = connection.execute(
                    "SELECT content FROM messages WHERE platform = 'facebook'"
                ).fetchone()[0]
                self.assertEqual(repaired, "It’s café time")
                duplicates = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'duplicate_records_ignored'"
                ).fetchone()[0]
                self.assertEqual(duplicates, "1")

            query = subprocess.run(
                [
                    sys.executable,
                    str(QUERY_SCRIPT),
                    "--db",
                    str(database),
                    "--query",
                    "café",
                    "--platform",
                    "facebook",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            results = json.loads(query.stdout)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["platform"], "facebook")
            self.assertIn("[café]", results[0]["snippet"])

            stats = subprocess.run(
                [
                    sys.executable,
                    str(QUERY_SCRIPT),
                    "--db",
                    str(database),
                    "--stats",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            stats_payload = json.loads(stats.stdout)
            self.assertEqual(stats_payload["metadata"]["total_records"], "2")
            self.assertEqual(
                stats_payload["metadata"]["platform_counts"],
                {"facebook": 1, "instagram": 1},
            )


if __name__ == "__main__":
    unittest.main()
