from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "archive_discord_guild.py"
SPEC = importlib.util.spec_from_file_location("archive_discord_guild", SCRIPT)
assert SPEC and SPEC.loader
archive = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = archive
SPEC.loader.exec_module(archive)


def write_config(path: Path, *, all_visible: bool = True) -> archive.ArchiveConfig:
    path.write_text(
        json.dumps(
            {
                "guild_id": "123456789012345678",
                "scope": {
                    "include_all_bot_visible": all_visible,
                    "include_channel_ids": ([] if all_visible else ["200"]),
                    "exclude_channel_ids": [],
                },
                "include_archived_threads": True,
                "include_joined_private_threads": True,
                "download_attachments": False,
            }
        ),
        encoding="utf-8",
    )
    return archive.ArchiveConfig.from_path(path)


def fake_message(message_id: str, content: str = "Example link https://example.com/a") -> dict:
    return {
        "id": message_id,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "edited_timestamp": None,
        "content": content,
        "type": 0,
        "flags": 0,
        "pinned": False,
        "mention_everyone": False,
        "author": {
            "id": "900000000000000001",
            "username": "exampleuser",
            "global_name": "Example User",
        },
        "member": {"nick": "Example Member"},
        "attachments": [
            {
                "id": f"8{message_id[-17:]}",
                "filename": "example.txt",
                "description": "Example attachment",
                "content_type": "text/plain",
                "size": 12,
                "url": "https://cdn.example.com/example.txt",
                "proxy_url": "https://proxy.example.com/example.txt",
            }
        ],
        "embeds": [{"url": "https://example.com/embed"}],
        "components": [],
        "reactions": [
            {
                "emoji": {"id": None, "name": "✅"},
                "count": 2,
                "count_details": {"burst": 0, "normal": 2},
                "me": False,
                "me_burst": False,
                "burst_colors": [],
            }
        ],
    }


class FakeDiscordClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []
        self.message_content_flags = archive.GATEWAY_MESSAGE_CONTENT_LIMITED
        self.message_pages: dict[str | None, list[dict]] = {
            None: [fake_message("120000000000000003"), fake_message("120000000000000002")],
            "120000000000000002": [fake_message("120000000000000001", "Older")],
        }

    def get(self, route: str, params: dict | None = None):
        self.calls.append((route, params))
        if route == "/users/@me":
            return {"id": "999", "username": "archivebot"}
        if route == "/oauth2/applications/@me":
            return {
                "id": "998",
                "name": "Archive App",
                "flags": self.message_content_flags,
            }
        if route == "/guilds/123456789012345678":
            return {
                "id": "123456789012345678",
                "name": "Example Guild",
                "roles": [
                    {
                        "id": "123456789012345678",
                        "permissions": str(archive.MINIMUM_PERMISSION_INTEGER),
                    }
                ],
            }
        if route == "/guilds/123456789012345678/members/999":
            return {"user": {"id": "999"}, "roles": []}
        if route == "/guilds/123456789012345678/channels":
            return [
                {
                    "id": "200",
                    "type": 0,
                    "name": "general",
                    "parent_id": "100",
                    "permission_overwrites": [],
                },
                {
                    "id": "201",
                    "type": 15,
                    "name": "forum",
                    "parent_id": "100",
                    "permission_overwrites": [],
                },
            ]
        if route == "/guilds/123456789012345678/threads/active":
            return {
                "threads": [
                    {"id": "300", "type": 11, "name": "active", "parent_id": "200"}
                ]
            }
        if route == "/channels/200/threads/archived/public":
            return {"threads": [], "has_more": False}
        if route == "/channels/200/users/@me/threads/archived/private":
            return {"threads": [], "has_more": False}
        if route == "/channels/201/threads/archived/public":
            return {
                "threads": [
                    {
                        "id": "301",
                        "type": 11,
                        "name": "archived",
                        "parent_id": "201",
                        "thread_metadata": {
                            "archive_timestamp": "2024-01-01T00:00:00+00:00"
                        },
                    }
                ],
                "has_more": False,
            }
        if route == "/channels/201/users/@me/threads/archived/private":
            return {"threads": [], "has_more": False}
        if route == "/channels/200/messages":
            return self.message_pages.get((params or {}).get("before"), [])
        raise AssertionError(f"unexpected route: {route} {params}")


class DiscordArchiveTest(unittest.TestCase):
    def test_permission_manifest_is_read_only(self) -> None:
        manifest = archive.permission_manifest("123456789012345678")
        self.assertEqual(manifest["permission_integer"], 66560)
        self.assertEqual(set(manifest["oauth_scopes"]), {"bot"})
        self.assertIn("permissions=66560", manifest["install_url"])
        self.assertIn("SEND_MESSAGES", manifest["explicitly_not_requested"])
        self.assertIn("ADMINISTRATOR", manifest["explicitly_not_requested"])

    def test_init_creates_private_pending_permission_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = write_config(root / "config.json")
            archive_root = root / "archive"
            paths = archive.initialize_archive(archive_root, config)
            receipt = archive.load_json(paths["permission"])
            self.assertEqual(receipt["status"], "pending")
            self.assertEqual(receipt["guild_id"], config.guild_id)
            self.assertEqual(paths["permission"].stat().st_mode & 0o777, 0o600)
            self.assertEqual(archive_root.stat().st_mode & 0o777, 0o700)
            for directory in (
                archive_root / "raw",
                paths["raw"],
                archive_root / "raw" / "attachments",
                paths["attachments"],
                paths["index"].parent,
                paths["checkpoint"].parent,
            ):
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            with self.assertRaises(PermissionError):
                archive.validate_permission_receipt(paths["permission"], config.guild_id)

    def test_preflight_inventories_metadata_without_message_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = write_config(root / "config.json")
            client = FakeDiscordClient()
            result = archive.preflight(client, config, root / "archive")
            surface_ids = {item["id"] for item in result["message_surfaces"]}
            self.assertEqual(surface_ids, {"200", "300", "301"})
            self.assertTrue(result["application"]["message_content_access"])
            self.assertFalse(any(route.endswith("/messages") for route, _ in client.calls))

    def test_channel_overwrites_remove_denied_parent_from_bot_scope(self) -> None:
        guild = {
            "id": "1",
            "roles": [{"id": "1", "permissions": str(archive.MINIMUM_PERMISSION_INTEGER)}],
        }
        member = {"roles": []}
        denied = {
            "id": "2",
            "permission_overwrites": [
                {"id": "1", "type": 0, "allow": "0", "deny": str(archive.VIEW_CHANNEL)}
            ],
        }
        self.assertFalse(
            archive.bot_channel_permissions(guild, member, denied, "9")
            & archive.VIEW_CHANNEL
        )

    def test_export_stops_before_api_calls_while_permission_is_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = write_config(root / "config.json")
            client = FakeDiscordClient()
            with self.assertRaises(PermissionError):
                archive.run_export(client, config, root / "archive")
            self.assertEqual(client.calls, [])

    def test_export_stops_before_message_calls_without_message_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = write_config(root / "config.json")
            archive_root = root / "archive"
            paths = archive.initialize_archive(archive_root, config)
            receipt = archive.load_json(paths["permission"])
            receipt.update(
                {
                    "status": "approved",
                    "approved_by": "Example Admin",
                    "approved_at": "2024-01-01T00:00:00+00:00",
                    "approved_scope": "Example approved channels",
                    "takedown_contact": "Example Admin",
                }
            )
            archive.atomic_write_json(paths["permission"], receipt)
            client = FakeDiscordClient()
            client.message_content_flags = 0
            with self.assertRaises(PermissionError):
                archive.run_export(client, config, archive_root)
            self.assertFalse(any(route.endswith("/messages") for route, _ in client.calls))

    def test_export_page_checkpoint_index_query_and_dedupe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = write_config(root / "config.json")
            archive_root = root / "archive"
            paths = archive.initialize_archive(archive_root, config)
            surface = {"id": "200", "type": 0, "name": "general", "parent_id": "100"}
            checkpoint = archive.load_json(paths["checkpoint"])
            client = FakeDiscordClient()
            pages, messages = archive.export_surface(
                client, surface, paths, checkpoint
            )
            self.assertEqual((pages, messages), (1, 2))
            self.assertTrue(checkpoint["surfaces"]["200"]["complete"])
            metadata = archive.build_index(archive_root, config)
            self.assertEqual(metadata["message_count"], 2)
            self.assertEqual(metadata["duplicate_records_ignored"], 0)
            database = paths["index"]
            self.assertEqual(archive.stats(database)["messages"], 2)
            results = archive.query_index(database, "Example", 10)
            self.assertEqual(len(results), 2)
            self.assertTrue(results[0]["author_pseudonym"].startswith("member-"))
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM attachments").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM reactions").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM links").fetchone()[0], 4)

    def test_takedown_rewrites_raw_and_rebuilds_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = write_config(root / "config.json")
            archive_root = root / "archive"
            paths = archive.initialize_archive(archive_root, config)
            surface = {"id": "200", "type": 0, "name": "general", "parent_id": "100"}
            checkpoint = archive.load_json(paths["checkpoint"])
            archive.export_surface(FakeDiscordClient(), surface, paths, checkpoint)
            archive.build_index(archive_root, config)
            attachment_body = paths["attachments"] / "ab" / "example-body"
            attachment_body.parent.mkdir(parents=True, exist_ok=True)
            attachment_body.write_bytes(b"example")
            with sqlite3.connect(paths["index"]) as connection:
                connection.execute(
                    "UPDATE attachments SET local_path=? WHERE message_id=?",
                    (
                        str(attachment_body.relative_to(archive_root)),
                        "120000000000000002",
                    ),
                )
                connection.commit()
            result = archive.run_takedown(
                archive_root,
                config,
                {"120000000000000002"},
                "test removal",
            )
            self.assertEqual(result["messages_removed"], 1)
            self.assertEqual(result["attachment_bodies_removed"], 1)
            self.assertFalse(attachment_body.exists())
            self.assertEqual(archive.stats(paths["index"])["messages"], 1)
            receipt_lines = paths["takedowns"].read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(receipt_lines), 1)
            self.assertEqual(json.loads(receipt_lines[0])["reason"], "test removal")

    def test_token_must_come_from_bot_environment_variable(self) -> None:
        previous = os.environ.pop("DISCORD_BOT_TOKEN", None)
        try:
            with self.assertRaises(PermissionError):
                archive.require_bot_token()
        finally:
            if previous is not None:
                os.environ["DISCORD_BOT_TOKEN"] = previous


if __name__ == "__main__":
    unittest.main()
