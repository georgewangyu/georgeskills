# Exports Ops

Modular export implementations for:
- Apple Notes
- Google Calendar
- Gmail
- large, verified Google Drive folder archives
- Meta Facebook and Instagram JSON archives
- Cursor chats
- X/Twitter feed snapshots

The scripts run against private data/config in `<private-repo>`:
- `captures/*`
- `scripts/exports/*` credentials/config/tokens

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
