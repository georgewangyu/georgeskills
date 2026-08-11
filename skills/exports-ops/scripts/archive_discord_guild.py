#!/usr/bin/env python3
"""Archive bot-visible Discord guild history through the official API.

This tool deliberately accepts only a Discord bot token from the
``DISCORD_BOT_TOKEN`` environment variable. It never accepts a normal user
token, never sends messages, and does not request moderation permissions.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


API_BASE = "https://discord.com/api/v10"
VIEW_CHANNEL = 1 << 10
READ_MESSAGE_HISTORY = 1 << 16
ADMINISTRATOR = 1 << 3
GATEWAY_MESSAGE_CONTENT = 1 << 18
GATEWAY_MESSAGE_CONTENT_LIMITED = 1 << 19
MINIMUM_PERMISSION_INTEGER = VIEW_CHANNEL | READ_MESSAGE_HISTORY
TEXT_CHANNEL_TYPES = {0, 5}
THREAD_CHANNEL_TYPES = {10, 11, 12}
THREAD_PARENT_TYPES = {0, 5, 15, 16}
URL_RE = re.compile(r"https?://[^\s<>\]\[()]+")
SCHEMA_VERSION = "discord-offline-archive-v1"


class DiscordAPIError(RuntimeError):
    """Raised for an unsuccessful Discord API response."""

    def __init__(self, status: int, route: str, detail: str) -> None:
        super().__init__(f"Discord API {status} for {route}: {detail}")
        self.status = status
        self.route = route


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_json(value) + b"\n")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, canonical_json(value) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def snowflake_timestamp(value: str) -> str:
    milliseconds = (int(value) >> 22) + 1420070400000
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat()


@dataclass(frozen=True)
class ArchiveConfig:
    guild_id: str
    include_all_bot_visible: bool
    include_channel_ids: frozenset[str]
    exclude_channel_ids: frozenset[str]
    include_archived_threads: bool
    include_joined_private_threads: bool
    download_attachments: bool
    max_attachment_bytes: int

    @classmethod
    def from_path(cls, path: Path) -> "ArchiveConfig":
        payload = load_json(path)
        scope = payload.get("scope") or {}
        if not isinstance(scope, dict):
            raise ValueError("config.scope must be an object")
        guild_id = str(payload.get("guild_id") or "").strip()
        if not guild_id.isdigit():
            raise ValueError("config.guild_id must be a Discord snowflake")
        include = frozenset(str(value) for value in scope.get("include_channel_ids", []))
        exclude = frozenset(str(value) for value in scope.get("exclude_channel_ids", []))
        include_all = bool(scope.get("include_all_bot_visible", False))
        if not include_all and not include:
            raise ValueError(
                "scope must set include_all_bot_visible=true or list include_channel_ids"
            )
        max_bytes = int(payload.get("max_attachment_bytes", 100 * 1024 * 1024))
        if max_bytes < 1:
            raise ValueError("max_attachment_bytes must be positive")
        return cls(
            guild_id=guild_id,
            include_all_bot_visible=include_all,
            include_channel_ids=include,
            exclude_channel_ids=exclude,
            include_archived_threads=bool(payload.get("include_archived_threads", True)),
            include_joined_private_threads=bool(
                payload.get("include_joined_private_threads", True)
            ),
            download_attachments=bool(payload.get("download_attachments", False)),
            max_attachment_bytes=max_bytes,
        )

    def includes_parent(self, channel_id: str) -> bool:
        if channel_id in self.exclude_channel_ids:
            return False
        return self.include_all_bot_visible or channel_id in self.include_channel_ids

    def includes_surface(self, channel_id: str, parent_id: str | None) -> bool:
        if channel_id in self.exclude_channel_ids:
            return False
        if parent_id and parent_id in self.exclude_channel_ids:
            return False
        return self.includes_parent(channel_id) or bool(
            parent_id and self.includes_parent(parent_id)
        )


class DiscordClient:
    def __init__(
        self,
        token: str,
        *,
        api_base: str = API_BASE,
        sleep: Any = time.sleep,
        max_attempts: int = 8,
    ) -> None:
        if not token or any(character.isspace() for character in token):
            raise ValueError("DISCORD_BOT_TOKEN is missing or malformed")
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.sleep = sleep
        self.max_attempts = max_attempts

    def get(self, route: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{self.api_base}{route}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bot {self.token}",
                "User-Agent": "PrivateDiscordArchive/1.0",
                "Accept": "application/json",
            },
            method="GET",
        )
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = response.read()
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    reset_after = response.headers.get("X-RateLimit-Reset-After")
                    if remaining == "0" and reset_after:
                        self.sleep(max(0.0, float(reset_after)))
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as error:
                body = error.read()
                detail = body.decode("utf-8", "replace")[:1000]
                if error.code == 429 and attempt < self.max_attempts:
                    try:
                        payload = json.loads(body)
                        retry_after = float(payload.get("retry_after", 1.0))
                    except (ValueError, TypeError, json.JSONDecodeError):
                        retry_after = float(error.headers.get("Retry-After", "1"))
                    self.sleep(max(0.0, retry_after))
                    continue
                raise DiscordAPIError(error.code, route, detail) from error
            except urllib.error.URLError as error:
                if attempt >= self.max_attempts:
                    raise RuntimeError(f"network failure for {route}: {error.reason}") from error
                self.sleep(min(2 ** (attempt - 1), 30))
        raise AssertionError("unreachable")


def oauth_install_url(application_id: str) -> str:
    if not application_id.isdigit():
        raise ValueError("application_id must be a Discord snowflake")
    query = urllib.parse.urlencode(
        {
            "client_id": application_id,
            "scope": "bot",
            "permissions": str(MINIMUM_PERMISSION_INTEGER),
            "disable_guild_select": "true",
        }
    )
    return f"https://discord.com/oauth2/authorize?{query}"


def permission_manifest(application_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "discord-read-only-permission-manifest-v1",
        "oauth_scopes": ["bot"],
        "bot_permissions": {
            "VIEW_CHANNEL": VIEW_CHANNEL,
            "READ_MESSAGE_HISTORY": READ_MESSAGE_HISTORY,
        },
        "permission_integer": MINIMUM_PERMISSION_INTEGER,
        "gateway_intents": {
            "GUILDS": "required for guild/channel metadata",
            "MESSAGE_CONTENT": (
                "enable in the Discord Developer Portal when content, embeds, "
                "attachments, and components are required"
            ),
        },
        "explicitly_not_requested": [
            "SEND_MESSAGES",
            "MANAGE_MESSAGES",
            "MANAGE_CHANNELS",
            "MANAGE_THREADS",
            "MANAGE_GUILD",
            "MANAGE_WEBHOOKS",
            "KICK_MEMBERS",
            "BAN_MEMBERS",
            "ADMINISTRATOR",
        ],
    }
    if application_id:
        result["application_id"] = application_id
        result["install_url"] = oauth_install_url(application_id)
    return result


def archive_paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "raw": root / "raw" / "pages",
        "attachments": root / "raw" / "attachments" / "sha256",
        "index": root / "index" / "archive.sqlite",
        "jsonl": root / "index" / "messages.jsonl",
        "derived": root / "derived",
        "checkpoint": root / "state" / "checkpoint.json",
        "page_manifest": root / "state" / "page-manifest.jsonl",
        "permission": root / "permission-receipt.json",
        "inventory": root / "state" / "bot-visible-inventory.json",
        "salt": root / "state" / ".pseudonym-salt",
        "takedowns": root / "state" / "takedowns.jsonl",
    }


def initialize_archive(root: Path, config: ArchiveConfig) -> dict[str, Path]:
    paths = archive_paths(root)
    directories = (
        paths["root"],
        paths["root"] / "raw",
        paths["raw"],
        paths["root"] / "raw" / "attachments",
        paths["attachments"],
        paths["derived"],
        paths["checkpoint"].parent,
        paths["index"].parent,
    )
    for directory in directories:
        require_private_directory(directory)
    if not paths["salt"].exists():
        atomic_write(paths["salt"], secrets.token_bytes(32))
    if not paths["checkpoint"].exists():
        atomic_write_json(
            paths["checkpoint"],
            {"schema": SCHEMA_VERSION, "guild_id": config.guild_id, "surfaces": {}},
        )
    if not paths["permission"].exists():
        atomic_write_json(
            paths["permission"],
            {
                "schema": "discord-source-permission-receipt-v1",
                "status": "pending",
                "guild_id": config.guild_id,
                "purpose": "private offline reading and search",
                "approved_by": None,
                "approved_at": None,
                "approved_scope": None,
                "retention": "until no longer needed or a valid takedown request",
                "takedown_contact": None,
                "notes": "Complete this receipt before running export.",
            },
        )
    return paths


def validate_permission_receipt(path: Path, guild_id: str) -> dict[str, Any]:
    receipt = load_json(path)
    if str(receipt.get("guild_id")) != guild_id:
        raise ValueError("permission receipt guild_id does not match config")
    missing = [
        field
        for field in ("approved_by", "approved_at", "approved_scope", "takedown_contact")
        if not receipt.get(field)
    ]
    if receipt.get("status") != "approved" or missing:
        detail = ", ".join(missing) if missing else "status=approved"
        raise PermissionError(
            "source permission receipt is incomplete; required: " + detail
        )
    return receipt


def channel_summary(channel: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(channel.get("id")),
        "type": channel.get("type"),
        "name": channel.get("name"),
        "parent_id": channel.get("parent_id"),
        "thread_metadata": channel.get("thread_metadata"),
    }


def bot_channel_permissions(
    guild: dict[str, Any],
    member: dict[str, Any],
    channel: dict[str, Any],
    bot_id: str,
) -> int:
    """Compute the bot member's effective guild-channel permissions."""
    role_ids = {str(value) for value in member.get("roles", [])}
    role_ids.add(str(guild["id"]))
    permissions = 0
    for role in guild.get("roles", []):
        if str(role.get("id")) in role_ids:
            permissions |= int(role.get("permissions", "0"))
    if permissions & ADMINISTRATOR:
        return (1 << 64) - 1

    overwrites = channel.get("permission_overwrites") or []
    everyone = next(
        (
            overwrite
            for overwrite in overwrites
            if str(overwrite.get("id")) == str(guild["id"])
            and int(overwrite.get("type", 0)) == 0
        ),
        None,
    )
    if everyone:
        permissions &= ~int(everyone.get("deny", "0"))
        permissions |= int(everyone.get("allow", "0"))

    role_deny = 0
    role_allow = 0
    for overwrite in overwrites:
        if int(overwrite.get("type", 0)) != 0:
            continue
        if str(overwrite.get("id")) not in role_ids:
            continue
        role_deny |= int(overwrite.get("deny", "0"))
        role_allow |= int(overwrite.get("allow", "0"))
    permissions &= ~role_deny
    permissions |= role_allow

    member_overwrite = next(
        (
            overwrite
            for overwrite in overwrites
            if str(overwrite.get("id")) == bot_id
            and int(overwrite.get("type", 0)) == 1
        ),
        None,
    )
    if member_overwrite:
        permissions &= ~int(member_overwrite.get("deny", "0"))
        permissions |= int(member_overwrite.get("allow", "0"))
    return permissions


def iter_archived_threads(
    client: DiscordClient,
    parent_id: str,
    route_suffix: str,
    *,
    before_kind: str = "archive_timestamp",
) -> Iterator[dict[str, Any]]:
    before: str | None = None
    while True:
        params: dict[str, Any] = {"limit": 100}
        if before:
            params["before"] = before
        route = f"/channels/{parent_id}/{route_suffix}"
        payload = client.get(route, params)
        threads = payload.get("threads", []) if isinstance(payload, dict) else []
        for thread in threads:
            yield thread
        if not payload.get("has_more") or not threads:
            break
        if before_kind == "thread_id":
            before = str(threads[-1].get("id") or "")
        else:
            metadata = threads[-1].get("thread_metadata") or {}
            before = metadata.get("archive_timestamp")
        if not before:
            break


def discover_surfaces(
    client: DiscordClient,
    config: ArchiveConfig,
    *,
    bot: dict[str, Any] | None = None,
    guild: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bot = bot or client.get("/users/@me")
    guild = guild or client.get(f"/guilds/{config.guild_id}")
    bot_id = str(bot["id"])
    member = client.get(f"/guilds/{config.guild_id}/members/{bot_id}")
    channels = client.get(f"/guilds/{config.guild_id}/channels")
    if not isinstance(channels, list):
        raise RuntimeError("Discord did not return a guild channel list")
    selected_parents = [
        channel
        for channel in channels
        if config.includes_parent(str(channel.get("id")))
        and bot_channel_permissions(guild, member, channel, bot_id) & VIEW_CHANNEL
    ]
    surfaces: dict[str, dict[str, Any]] = {}
    for channel in selected_parents:
        channel_id = str(channel.get("id"))
        if channel.get("type") in TEXT_CHANNEL_TYPES:
            surfaces[channel_id] = channel

    active = client.get(f"/guilds/{config.guild_id}/threads/active")
    for thread in (active or {}).get("threads", []):
        thread_id = str(thread.get("id"))
        parent_id = str(thread.get("parent_id") or "")
        if config.includes_surface(thread_id, parent_id):
            surfaces[thread_id] = thread

    if config.include_archived_threads:
        for parent in selected_parents:
            if parent.get("type") not in THREAD_PARENT_TYPES:
                continue
            parent_id = str(parent.get("id"))
            try:
                for thread in iter_archived_threads(
                    client, parent_id, "threads/archived/public"
                ):
                    thread_id = str(thread.get("id"))
                    if config.includes_surface(thread_id, parent_id):
                        surfaces[thread_id] = thread
            except DiscordAPIError as error:
                if error.status != 403:
                    raise
            if config.include_joined_private_threads:
                try:
                    for thread in iter_archived_threads(
                        client,
                        parent_id,
                        "users/@me/threads/archived/private",
                        before_kind="thread_id",
                    ):
                        thread_id = str(thread.get("id"))
                        if config.includes_surface(thread_id, parent_id):
                            surfaces[thread_id] = thread
                except DiscordAPIError as error:
                    if error.status != 403:
                        raise
    return selected_parents, sorted(surfaces.values(), key=lambda item: int(item["id"]))


def preflight(
    client: DiscordClient,
    config: ArchiveConfig,
    root: Path,
) -> dict[str, Any]:
    paths = initialize_archive(root, config)
    bot = client.get("/users/@me")
    application = client.get("/oauth2/applications/@me")
    guild = client.get(f"/guilds/{config.guild_id}")
    parents, surfaces = discover_surfaces(client, config, bot=bot, guild=guild)
    application_flags = int(application.get("flags_new") or application.get("flags") or 0)
    message_content_access = bool(
        application_flags
        & (GATEWAY_MESSAGE_CONTENT | GATEWAY_MESSAGE_CONTENT_LIMITED)
    )
    inventory = {
        "schema": "discord-bot-visible-inventory-v1",
        "created_at": utc_now(),
        "guild": {"id": guild.get("id"), "name": guild.get("name")},
        "bot": {"id": bot.get("id"), "username": bot.get("username")},
        "application": {
            "id": application.get("id"),
            "name": application.get("name"),
            "message_content_access": message_content_access,
        },
        "selected_parents": [channel_summary(value) for value in parents],
        "message_surfaces": [channel_summary(value) for value in surfaces],
        "scope_note": (
            "This is bot-visible metadata, not a claim that the bot and a human "
            "member have identical channel access. No message endpoint was called."
        ),
    }
    atomic_write_json(paths["inventory"], inventory)
    return inventory


def page_path(raw_root: Path, surface_id: str, messages: list[dict[str, Any]]) -> Path:
    newest = max(int(message["id"]) for message in messages)
    oldest = min(int(message["id"]) for message in messages)
    return raw_root / surface_id / f"{newest}-{oldest}.json"


def export_surface(
    client: DiscordClient,
    surface: dict[str, Any],
    paths: dict[str, Path],
    checkpoint: dict[str, Any],
) -> tuple[int, int]:
    surface_id = str(surface["id"])
    state = checkpoint.setdefault("surfaces", {}).setdefault(
        surface_id,
        {
            "complete": False,
            "before": None,
            "pages": 0,
            "messages": 0,
            "surface": channel_summary(surface),
        },
    )
    if state.get("complete"):
        return 0, 0
    pages_written = 0
    messages_written = 0
    while True:
        params: dict[str, Any] = {"limit": 100}
        if state.get("before"):
            params["before"] = state["before"]
        route = f"/channels/{surface_id}/messages"
        messages = client.get(route, params)
        if not isinstance(messages, list):
            raise RuntimeError(f"unexpected message response for {surface_id}")
        if not messages:
            state["complete"] = True
            state["completed_at"] = utc_now()
            atomic_write_json(paths["checkpoint"], checkpoint)
            break
        raw_payload = {
            "schema": SCHEMA_VERSION,
            "guild_id": checkpoint["guild_id"],
            "surface": channel_summary(surface),
            "fetched_at": utc_now(),
            "request": {"route": route, "before": state.get("before"), "limit": 100},
            "messages": messages,
        }
        raw_bytes = canonical_json(raw_payload) + b"\n"
        target = page_path(paths["raw"], surface_id, messages)
        digest = sha256_bytes(raw_bytes)
        if target.exists():
            if sha256_bytes(target.read_bytes()) != digest:
                raise RuntimeError(f"raw page hash mismatch: {target}")
        else:
            atomic_write(target, raw_bytes)
            append_jsonl(
                paths["page_manifest"],
                {
                    "surface_id": surface_id,
                    "path": str(target.relative_to(paths["root"])),
                    "sha256": digest,
                    "message_count": len(messages),
                    "fetched_at": raw_payload["fetched_at"],
                },
            )
            pages_written += 1
            messages_written += len(messages)
        oldest = min(messages, key=lambda message: int(message["id"]))
        state["before"] = str(oldest["id"])
        state["pages"] = int(state.get("pages", 0)) + 1
        state["messages"] = int(state.get("messages", 0)) + len(messages)
        state["updated_at"] = utc_now()
        atomic_write_json(paths["checkpoint"], checkpoint)
        if len(messages) < 100:
            state["complete"] = True
            state["completed_at"] = utc_now()
            atomic_write_json(paths["checkpoint"], checkpoint)
            break
    return pages_written, messages_written


def pseudonym(salt: bytes, author_id: str) -> str:
    digest = hmac.new(salt, author_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"member-{digest[:12]}"


def iter_raw_messages(raw_root: Path) -> Iterator[tuple[dict[str, Any], dict[str, Any], Path]]:
    for page in sorted(raw_root.glob("*/*.json")):
        payload = load_json(page)
        surface = payload.get("surface") or {}
        for message in payload.get("messages", []):
            if isinstance(message, dict):
                yield surface, message, page


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE archive_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE surfaces (
            surface_id TEXT PRIMARY KEY,
            parent_id TEXT,
            surface_type INTEGER,
            name TEXT,
            metadata_json TEXT NOT NULL
        );
        CREATE TABLE authors (
            author_id TEXT PRIMARY KEY,
            author_pseudonym TEXT NOT NULL,
            username TEXT,
            global_name TEXT,
            latest_display_name TEXT,
            author_json TEXT NOT NULL
        );
        CREATE TABLE messages (
            message_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            surface_id TEXT NOT NULL,
            author_id TEXT,
            author_pseudonym TEXT,
            created_at TEXT NOT NULL,
            edited_at TEXT,
            content TEXT NOT NULL,
            message_type INTEGER,
            flags INTEGER,
            pinned INTEGER NOT NULL,
            mention_everyone INTEGER NOT NULL,
            reference_json TEXT NOT NULL,
            embeds_json TEXT NOT NULL,
            components_json TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            source_page TEXT NOT NULL
        );
        CREATE TABLE attachments (
            attachment_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            filename TEXT,
            description TEXT,
            content_type TEXT,
            size INTEGER,
            source_url TEXT,
            proxy_url TEXT,
            width INTEGER,
            height INTEGER,
            sha256 TEXT,
            local_path TEXT
        );
        CREATE TABLE reactions (
            message_id TEXT NOT NULL,
            emoji_key TEXT NOT NULL,
            emoji_name TEXT,
            emoji_id TEXT,
            count INTEGER NOT NULL,
            count_details_json TEXT NOT NULL,
            me INTEGER NOT NULL,
            burst_me INTEGER NOT NULL,
            burst_colors_json TEXT NOT NULL,
            PRIMARY KEY(message_id, emoji_key)
        );
        CREATE TABLE links (
            message_id TEXT NOT NULL,
            url TEXT NOT NULL,
            PRIMARY KEY(message_id, url)
        );
        CREATE INDEX messages_surface_created_idx ON messages(surface_id, created_at);
        CREATE INDEX messages_author_created_idx ON messages(author_id, created_at);
        CREATE INDEX attachments_message_idx ON attachments(message_id);
        CREATE VIRTUAL TABLE messages_fts USING fts5(
            content,
            author_pseudonym,
            surface_id,
            content='messages',
            content_rowid='rowid',
            tokenize='unicode61 remove_diacritics 2'
        );
        """
    )


def insert_message(
    connection: sqlite3.Connection,
    guild_id: str,
    surface: dict[str, Any],
    message: dict[str, Any],
    source_page: Path,
    salt: bytes,
) -> bool:
    message_id = str(message["id"])
    author = message.get("author") or {}
    author_id = str(author.get("id")) if author.get("id") else None
    member = message.get("member") or {}
    author_alias = pseudonym(salt, author_id) if author_id else None
    connection.execute(
        """
        INSERT OR IGNORE INTO surfaces(surface_id,parent_id,surface_type,name,metadata_json)
        VALUES(?,?,?,?,?)
        """,
        (
            str(surface.get("id")),
            surface.get("parent_id"),
            surface.get("type"),
            surface.get("name"),
            json.dumps(surface, ensure_ascii=False, sort_keys=True),
        ),
    )
    if author_id:
        connection.execute(
            """
            INSERT INTO authors(
                author_id,author_pseudonym,username,global_name,latest_display_name,author_json
            ) VALUES(?,?,?,?,?,?)
            ON CONFLICT(author_id) DO UPDATE SET
                username=excluded.username,
                global_name=excluded.global_name,
                latest_display_name=excluded.latest_display_name,
                author_json=excluded.author_json
            """,
            (
                author_id,
                author_alias,
                author.get("username"),
                author.get("global_name"),
                member.get("nick") or author.get("global_name") or author.get("username"),
                json.dumps(author, ensure_ascii=False, sort_keys=True),
            ),
        )
    before = connection.total_changes
    connection.execute(
        """
        INSERT OR IGNORE INTO messages(
            message_id,guild_id,surface_id,author_id,author_pseudonym,created_at,
            edited_at,content,message_type,flags,pinned,mention_everyone,reference_json,
            embeds_json,components_json,raw_json,source_page
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            message_id,
            guild_id,
            str(surface.get("id")),
            author_id,
            author_alias,
            message.get("timestamp") or snowflake_timestamp(message_id),
            message.get("edited_timestamp"),
            message.get("content") or "",
            message.get("type"),
            message.get("flags"),
            int(bool(message.get("pinned"))),
            int(bool(message.get("mention_everyone"))),
            json.dumps(message.get("message_reference") or {}, ensure_ascii=False),
            json.dumps(message.get("embeds") or [], ensure_ascii=False),
            json.dumps(message.get("components") or [], ensure_ascii=False),
            json.dumps(message, ensure_ascii=False, sort_keys=True),
            str(source_page),
        ),
    )
    inserted = connection.total_changes > before
    if not inserted:
        return False
    for attachment in message.get("attachments") or []:
        connection.execute(
            """
            INSERT OR REPLACE INTO attachments(
                attachment_id,message_id,filename,description,content_type,size,source_url,
                proxy_url,width,height,sha256,local_path
            ) VALUES(?,?,?,?,?,?,?,?,?,?,NULL,NULL)
            """,
            (
                str(attachment.get("id")),
                message_id,
                attachment.get("filename"),
                attachment.get("description"),
                attachment.get("content_type"),
                attachment.get("size"),
                attachment.get("url"),
                attachment.get("proxy_url"),
                attachment.get("width"),
                attachment.get("height"),
            ),
        )
    for reaction in message.get("reactions") or []:
        emoji = reaction.get("emoji") or {}
        emoji_key = str(emoji.get("id") or emoji.get("name") or "unknown")
        connection.execute(
            """
            INSERT OR REPLACE INTO reactions(
                message_id,emoji_key,emoji_name,emoji_id,count,count_details_json,me,
                burst_me,burst_colors_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                message_id,
                emoji_key,
                emoji.get("name"),
                emoji.get("id"),
                int(reaction.get("count", 0)),
                json.dumps(reaction.get("count_details") or {}, ensure_ascii=False),
                int(bool(reaction.get("me"))),
                int(bool(reaction.get("me_burst"))),
                json.dumps(reaction.get("burst_colors") or [], ensure_ascii=False),
            ),
        )
    links = set(URL_RE.findall(message.get("content") or ""))
    for embed in message.get("embeds") or []:
        if embed.get("url"):
            links.add(str(embed["url"]))
    for url in sorted(links):
        connection.execute(
            "INSERT OR IGNORE INTO links(message_id,url) VALUES(?,?)",
            (message_id, url),
        )
    return True


def build_index(root: Path, config: ArchiveConfig) -> dict[str, Any]:
    paths = archive_paths(root)
    temporary = paths["index"].with_suffix(".sqlite.tmp")
    temporary.unlink(missing_ok=True)
    salt = paths["salt"].read_bytes()
    connection = sqlite3.connect(temporary)
    initialize_database(connection)
    inserted = 0
    duplicates = 0
    for surface, message, source_page in iter_raw_messages(paths["raw"]):
        if insert_message(
            connection, config.guild_id, surface, message, source_page, salt
        ):
            inserted += 1
        else:
            duplicates += 1
    connection.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    metadata = {
        "schema": SCHEMA_VERSION,
        "guild_id": config.guild_id,
        "built_at": utc_now(),
        "message_count": inserted,
        "duplicate_records_ignored": duplicates,
    }
    connection.executemany(
        "INSERT INTO archive_metadata(key,value) VALUES(?,?)",
        ((key, json.dumps(value, ensure_ascii=False)) for key, value in metadata.items()),
    )
    connection.commit()
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        connection.close()
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    connection.close()
    os.chmod(temporary, 0o600)
    os.replace(temporary, paths["index"])
    with sqlite3.connect(paths["index"]) as read_connection:
        rows = read_connection.execute(
            """
            SELECT raw_json FROM messages
            ORDER BY CAST(message_id AS INTEGER)
            """
        )
        jsonl = b"".join(
            json.dumps(json.loads(row[0]), ensure_ascii=False, sort_keys=True).encode("utf-8")
            + b"\n"
            for row in rows
        )
    atomic_write(paths["jsonl"], jsonl)
    return metadata


def download_attachments(root: Path, config: ArchiveConfig) -> dict[str, int]:
    paths = archive_paths(root)
    downloaded = 0
    skipped = 0
    with sqlite3.connect(paths["index"]) as connection:
        rows = connection.execute(
            """
            SELECT attachment_id,size,source_url FROM attachments
            WHERE source_url IS NOT NULL AND sha256 IS NULL
            ORDER BY attachment_id
            """
        ).fetchall()
        for attachment_id, size, source_url in rows:
            if size is not None and int(size) > config.max_attachment_bytes:
                skipped += 1
                continue
            request = urllib.request.Request(
                source_url,
                headers={"User-Agent": "PrivateDiscordArchive/1.0"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read(config.max_attachment_bytes + 1)
            if len(body) > config.max_attachment_bytes:
                skipped += 1
                continue
            digest = sha256_bytes(body)
            target = paths["attachments"] / digest[:2] / digest
            if not target.exists():
                atomic_write(target, body)
            connection.execute(
                "UPDATE attachments SET sha256=?,local_path=? WHERE attachment_id=?",
                (digest, str(target.relative_to(root)), attachment_id),
            )
            connection.commit()
            downloaded += 1
    return {"downloaded": downloaded, "skipped": skipped}


def run_export(
    client: DiscordClient,
    config: ArchiveConfig,
    root: Path,
) -> dict[str, Any]:
    paths = initialize_archive(root, config)
    validate_permission_receipt(paths["permission"], config.guild_id)
    inventory = preflight(client, config, root)
    if not inventory["application"]["message_content_access"]:
        raise PermissionError(
            "the approved bot does not have MESSAGE_CONTENT configured; "
            "message content, embeds, attachments, and components would be empty"
        )
    checkpoint = load_json(paths["checkpoint"])
    surfaces_by_id = {
        str(surface["id"]): surface for surface in inventory["message_surfaces"]
    }
    pages = 0
    messages = 0
    denied: list[str] = []
    for surface_id, surface in surfaces_by_id.items():
        try:
            new_pages, new_messages = export_surface(
                client, surface, paths, checkpoint
            )
            pages += new_pages
            messages += new_messages
        except DiscordAPIError as error:
            if error.status != 403:
                raise
            denied.append(surface_id)
    index_metadata = build_index(root, config)
    attachment_result = {"downloaded": 0, "skipped": 0}
    if config.download_attachments:
        attachment_result = download_attachments(root, config)
    result = {
        "schema": SCHEMA_VERSION,
        "completed_at": utc_now(),
        "new_pages": pages,
        "new_messages": messages,
        "indexed_messages": index_metadata["message_count"],
        "denied_surface_ids": denied,
        "attachments": attachment_result,
    }
    atomic_write_json(root / "manifest.json", result)
    return result


def query_index(database: Path, query: str | None, limit: int) -> list[dict[str, Any]]:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        if query:
            rows = connection.execute(
                """
                SELECT m.message_id,m.surface_id,m.author_pseudonym,m.created_at,
                       snippet(messages_fts,0,'[',']',' … ',24) AS snippet
                FROM messages_fts
                JOIN messages m ON m.rowid=messages_fts.rowid
                WHERE messages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT message_id,surface_id,author_pseudonym,created_at,
                       substr(content,1,240) AS snippet
                FROM messages ORDER BY CAST(message_id AS INTEGER) DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def stats(database: Path) -> dict[str, Any]:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        return {
            "messages": connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
            "surfaces": connection.execute("SELECT COUNT(*) FROM surfaces").fetchone()[0],
            "authors": connection.execute("SELECT COUNT(*) FROM authors").fetchone()[0],
            "attachments": connection.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
            "links": connection.execute("SELECT COUNT(*) FROM links").fetchone()[0],
        }


def remove_messages_from_raw(root: Path, message_ids: set[str]) -> dict[str, int]:
    paths = archive_paths(root)
    pages_changed = 0
    removed = 0
    for page in sorted(paths["raw"].glob("*/*.json")):
        payload = load_json(page)
        before = payload.get("messages", [])
        after = [message for message in before if str(message.get("id")) not in message_ids]
        if len(after) == len(before):
            continue
        removed += len(before) - len(after)
        pages_changed += 1
        if after:
            payload["messages"] = after
            payload["takedown_applied_at"] = utc_now()
            atomic_write_json(page, payload)
        else:
            page.unlink()
    return {"pages_changed": pages_changed, "messages_removed": removed}


def purge_attachment_bodies(root: Path, message_ids: set[str]) -> int:
    paths = archive_paths(root)
    if not paths["index"].exists():
        return 0
    placeholders = ",".join("?" for _ in message_ids)
    with sqlite3.connect(paths["index"]) as connection:
        rows = connection.execute(
            f"SELECT local_path FROM attachments "
            f"WHERE message_id IN ({placeholders}) AND local_path IS NOT NULL",
            tuple(sorted(message_ids, key=int)),
        ).fetchall()
    attachment_root = paths["attachments"].resolve()
    removed = 0
    for (relative_path,) in rows:
        target = (root / relative_path).resolve()
        if not target.is_relative_to(attachment_root):
            raise RuntimeError(f"refusing unsafe attachment takedown path: {target}")
        if target.exists():
            target.unlink()
            removed += 1
    return removed


def run_takedown(
    root: Path,
    config: ArchiveConfig,
    message_ids: set[str],
    reason: str,
) -> dict[str, Any]:
    if not message_ids:
        raise ValueError("at least one --message-id is required")
    attachment_bodies_removed = purge_attachment_bodies(root, message_ids)
    result = remove_messages_from_raw(root, message_ids)
    receipt = {
        "applied_at": utc_now(),
        "message_ids": sorted(message_ids, key=int),
        "reason": reason,
        "attachment_bodies_removed": attachment_bodies_removed,
        **result,
    }
    append_jsonl(archive_paths(root)["takedowns"], receipt)
    build_index(root, config)
    return receipt


def require_bot_token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise PermissionError(
            "DISCORD_BOT_TOKEN is not set. Use only an approved Discord bot token; "
            "never use a personal Discord user token."
        )
    return token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    permission = subparsers.add_parser("permissions", help="Print minimum permissions")
    permission.add_argument("--application-id")

    for command in ("init", "preflight", "export", "rebuild-index"):
        child = subparsers.add_parser(command)
        child.add_argument("--config", type=Path, required=True)
        child.add_argument("--archive-root", type=Path, required=True)

    query = subparsers.add_parser("query")
    query.add_argument("--database", type=Path, required=True)
    query.add_argument("--query")
    query.add_argument("--limit", type=int, default=20)
    query.add_argument("--stats", action="store_true")

    takedown = subparsers.add_parser("takedown")
    takedown.add_argument("--config", type=Path, required=True)
    takedown.add_argument("--archive-root", type=Path, required=True)
    takedown.add_argument("--message-id", action="append", required=True)
    takedown.add_argument("--reason", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "permissions":
        print(json.dumps(permission_manifest(args.application_id), indent=2))
        return 0
    if args.command == "query":
        payload = stats(args.database) if args.stats else query_index(
            args.database, args.query, args.limit
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    config = ArchiveConfig.from_path(args.config)
    root = args.archive_root.expanduser().resolve()
    if args.command == "init":
        paths = initialize_archive(root, config)
        print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2))
        return 0
    if args.command == "rebuild-index":
        print(json.dumps(build_index(root, config), indent=2))
        return 0
    if args.command == "takedown":
        print(
            json.dumps(
                run_takedown(root, config, set(args.message_id), args.reason),
                indent=2,
            )
        )
        return 0

    client = DiscordClient(require_bot_token())
    if args.command == "preflight":
        print(json.dumps(preflight(client, config, root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "export":
        print(json.dumps(run_export(client, config, root), ensure_ascii=False, indent=2))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DiscordAPIError, PermissionError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
