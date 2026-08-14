---
name: exports-ops
description: Umbrella skill for private export and import pipelines. Use this when the task spans multiple data sources or when no more specific export skill applies.
memory_tags:
  - domain:exports
  - workflow:data-ingestion
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - risk:high
---

# Exports Ops

## Trigger

Use this skill for reusable export/import automation:
- email/calendar exports
- Apple Notes and Cursor chat exports
- social feed ingestion/export
- private local screen-activity capture and derived contact sheets
- multi-source export workflows that touch more than one data source

Prefer the narrower skills when the intent is clear:
- `x-check-ops`
- `email-ops`
- `calendar-ops`
- `apple-notes-export-ops`
- `cursor-chat-export-ops`

## Boundaries

- Specification source: `liferepo` workflow docs
- Private state source: `<private-repo>/captures/` and `<private-repo>/scripts/exports/*` config/token files

## Current Script Surface

Implementations currently live in:
- `skills/exports-ops/scripts/`

Large Google Drive archive transfers use
`scripts/download_google_drive_archive.py`. It authenticates with Drive
read-only scope, supports interrupted-transfer resume, verifies expected byte
counts, and records optional SHA-256 checksums in an atomic manifest. Keep
credentials, OAuth tokens, manifests, and downloaded files in the configured
private state or external archive, never in this reusable skill repo.

Before transferring large ZIPs, use
`scripts/inventory_google_drive_zips.py` to read their central directories via
HTTP Range requests. This supports Drive-as-cold-storage workflows where only
selected members are fetched later.

Use `scripts/read_google_drive_zip_member.py` with the generated inventory to
preview or extract one exact member directly from Drive. Its stdout mode is
bounded by default so an accidental read cannot flood the terminal or disk.

Use `scripts/index_google_takeout_activity.py` on a verified selected ZIP to
turn My Activity HTML into a SQLite table plus FTS5 search index. Keep that
derived private index beside the external archive rather than in this repo.

Use `scripts/query_google_takeout_activity.py` for bounded, read-only JSON
searches against that index. Prefer its default result limit and add a service
filter when the question is narrow.

Use `scripts/index_meta_messages.py` to build one atomic SQLite/FTS5 index
directly from verified Facebook and Instagram JSON export ZIPs. Pass every ZIP
part from one snapshot as `--archive PLATFORM=ZIP`; keep the output beside the
private external archive. The indexer deduplicates repeated members, repairs
common Meta UTF-8 mojibake, and does not extract the raw ZIP trees.

Use `scripts/query_meta_messages.py` for bounded, read-only full-text, platform,
sender, thread, and UTC date-range queries. Prefer statistics or narrow filters
before returning private message snippets.

Use `scripts/index_imessage_messages.py` on a consistent, read-only macOS
Messages `chat.db` snapshot. The indexer uses the bundled Swift helper to
decode legacy `NSAttributedString` message bodies, preserves attachment
metadata without copying binaries into the derived index, and writes an atomic
SQLite/FTS5 index. Keep both snapshot and index in private external storage.

Use `scripts/query_imessage_messages.py` for bounded statistics, timeline,
chat, direction, service, and full-text queries. Use `--content-only` when a
claim depends on words appearing in message text. Participant previews are
capped so a group-chat query does not spill a full private roster.

Use `scripts/export_imessage_daily_context.py` for the separate daily-summary
context lane. It must use SQLite backup semantics to create a consistent
temporary copy of the live Messages database, query only that temporary copy,
omit attachment bodies, filter automated verification traffic by default, and
delete the database snapshot after extraction. The output is a short-lived,
ignored private staging file; agents should write derived day-level context to
the journal. A private workflow may allow bounded, directly relevant raw
excerpts, but raw handles, credentials, attachment bodies, and bulk message
dumps remain excluded. This daily lane does not replace or advance the
verified monthly archive checkpoint.

Use `scripts/audit_export_freshness.py` with a private freshness registry to
check mixed automatic and snapshot exports without mutating their checkpoints.
It understands per-account timestamp marker files and dated snapshot due dates;
keep private account names and archive paths in the registry, not this repo.

Use `scripts/capture_screen_activity.py` for a pauseable macOS screen capture
pilot. Raw images must go to a caller-configured private external archive; the
collector must wait when that volume is missing rather than fall back to an
internal disk. Keep the locked, idle, and sensitive-app exclusions enabled,
use rolling raw retention, and treat generated contact sheets and image-token
reports as analysis aids rather than permission to upload any screen content.
The script makes no model or network calls automatically.

Legacy entrypoints remain in `<private-repo>/scripts/exports/` as wrappers that
delegate to this skill.
