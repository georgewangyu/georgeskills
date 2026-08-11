# Exports Ops

Modular export implementations for:
- Apple Notes
- Google Calendar
- Gmail
- large, verified Google Drive folder archives
- Meta Facebook and Instagram JSON archives
- macOS Messages/iMessage snapshots
- Cursor chats
- X/Twitter feed snapshots
- local-first macOS screen-activity capture
- approved Discord guild history through a least-privilege bot

The scripts run against private data/config in `<private-repo>`:
- `captures/*`
- `scripts/exports/*` credentials/config/tokens

`scripts/archive_discord_guild.py` builds a private offline Discord archive
through the official bot API. It accepts only `DISCORD_BOT_TOKEN` from the
environment, requests no send or moderation permissions, refuses message
collection until a source-permission receipt is approved, and stores resumable
raw pages plus normalized JSONL/SQLite outside the reusable skill repository.
It inventories bot-visible channels and threads separately from human-visible
scope, follows `before` cursors and Discord rate-limit headers, and includes a
takedown command for active raw/index removal.

For a bounded Google Drive archive, use
`scripts/download_google_drive_archive.py` with explicit credentials, token,
manifest, output directory, folder ID, and optional account/date filters. Run
`--list-only` first, then download a small file by `--file-id` before starting
the full resumable transfer.

To leave large ZIPs in Drive and inspect them in place, use
`scripts/inventory_google_drive_zips.py`. It writes a gzipped member inventory
while fetching only the ZIP index ranges, not the archive bodies.

`scripts/read_google_drive_zip_member.py` uses that inventory to preview or
extract an exact member on demand without downloading the containing ZIP.

`scripts/index_google_takeout_activity.py` builds an external SQLite/FTS5 index
from the selected My Activity HTML files without extracting the ZIP tree.

`scripts/query_google_takeout_activity.py` reports index statistics or returns
bounded JSON search results from the read-only database.

`scripts/index_meta_messages.py` builds an atomic SQLite/FTS5 index directly
from every verified Facebook and Instagram ZIP part in one export snapshot. It
does not extract the archive trees and keeps private records in the caller's
chosen external/private output location.

`scripts/query_meta_messages.py` reports index statistics or returns bounded
read-only full-text, platform, sender, thread, and UTC date-range results.

`scripts/index_imessage_messages.py` builds an atomic SQLite/FTS5 index from a
consistent macOS Messages `chat.db` snapshot. Its bundled Swift decoder recovers
message text stored in Apple's legacy attributed-string format while retaining
attachment metadata rather than duplicating attachment binaries.

`scripts/query_imessage_messages.py` reports bounded statistics, timelines,
chat rankings, and full-text results with direction, service, chat, and date
filters. Use `--content-only` for message-body claims.

`scripts/export_imessage_daily_context.py` creates the lighter nightly context
surface used by a private daily-summary workflow. It snapshots `chat.db` with
SQLite backup semantics into a temporary directory, extracts the target local
day plus the previous day's late window, omits attachment content, filters
obvious automated traffic, writes a bounded private JSON staging file, and
deletes the temporary database when the process exits. It is intentionally
separate from the large verified archive/index workflow.

`scripts/audit_export_freshness.py` reads a caller-owned JSON registry and
reports stale incremental markers, due snapshots, and external-manifest
availability. It is deliberately read-only and does not advance checkpoints.

`scripts/capture_screen_activity.py` runs a pauseable macOS capture loop with
locked/idle/sensitive-app skips, external-volume-only raw storage, rolling raw
retention, 10-minute contact sheets, and a storage/image-token estimate. It
makes no network or model calls; private paths belong in caller-owned config.
