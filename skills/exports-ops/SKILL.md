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

Legacy entrypoints remain in `<private-repo>/scripts/exports/` as wrappers that
delegate to this skill.
