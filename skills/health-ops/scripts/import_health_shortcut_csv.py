#!/usr/bin/env python3
"""
Import Apple Shortcut health CSV from iCloud Drive into the configured private repo and sync metrics.

Default source:
~/Library/Mobile Documents/com~apple~CloudDocs/Shortcuts/daily_health_metrics.csv
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from health_paths import daily_health_metrics_csv
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
HEALTH_OPS_DIR = Path(__file__).resolve().parent
DEFAULT_ICLOUD_SOURCE = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Shortcuts"
    / "daily_health_metrics.csv"
)
DEST = daily_health_metrics_csv(ROOT)
SYNC_SCRIPT = HEALTH_OPS_DIR / "sync_health_shortcut_metrics.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import health CSV from iCloud and sync daily metrics")
    parser.add_argument("--source", default=str(DEFAULT_ICLOUD_SOURCE), help="iCloud source CSV path")
    parser.add_argument("--copy-only", action="store_true", help="Copy CSV only, skip sync")
    parser.add_argument("--write", action="store_true", help="Apply sync updates to daily_metrics.csv")
    parser.add_argument("--overwrite-existing", action="store_true", help="Overwrite existing sleep/exercise values")
    args = parser.parse_args()

    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"Source CSV not found: {source}")
        return 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, DEST)
    print(f"Copied health CSV to: {DEST}")

    if args.copy_only:
        return 0

    cmd = ["python3", str(SYNC_SCRIPT), "--health-csv", str(DEST)]
    if args.write:
        cmd.append("--write")
    if args.overwrite_existing:
        cmd.append("--overwrite-existing")

    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
