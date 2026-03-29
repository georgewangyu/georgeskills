#!/usr/bin/env python3
"""
Import Health Auto Export JSON exports from cloud-backed folders into the
canonical daily health metrics CSV used by the journal workflow.

This script works with both:

1. Google Drive automation exports
2. iCloud Drive/manual export JSON files from the app container
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from health_auto_export_rest_receiver import DEFAULT_DEST, DEFAULT_RAW_DIR, ingest_payload


DEFAULT_FOLDER_NAME = "LifeRepo Health"
DEFAULT_ICLOUD_MANUAL_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~com~ifunography~HealthExport"
    / "Documents"
    / "iCloud drive"
)


def default_drive_root() -> Path:
    cloud_storage = Path.home() / "Library" / "CloudStorage"
    candidates = sorted(cloud_storage.glob("GoogleDrive-*"))
    if candidates:
        return candidates[0] / "My Drive" / "Health Auto Export"
    return cloud_storage / "GoogleDrive" / "My Drive" / "Health Auto Export"


def find_latest_json(source_dir: Path) -> Path | None:
    candidates = sorted(
        source_dir.rglob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Health Auto Export Google Drive JSON into canonical daily_health_metrics.csv"
    )
    parser.add_argument(
        "--drive-root",
        default=str(default_drive_root()),
        help="Google Drive Health Auto Export root folder",
    )
    parser.add_argument(
        "--folder-name",
        default=DEFAULT_FOLDER_NAME,
        help="Automation folder name inside 'Health Auto Export'",
    )
    parser.add_argument(
        "--icloud-manual-dir",
        default=str(DEFAULT_ICLOUD_MANUAL_DIR),
        help="Fallback iCloud app Documents folder to scan for JSON exports",
    )
    parser.add_argument(
        "--input-json",
        default="",
        help="Explicit JSON export file path (overrides drive folder scan)",
    )
    parser.add_argument(
        "--dest-csv",
        default=str(DEFAULT_DEST),
        help="Canonical health CSV path",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directory to archive imported raw payloads",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Reserved for workflow compatibility; canonical health CSV is always updated",
    )
    args = parser.parse_args()

    if args.input_json:
        source = Path(args.input_json).expanduser()
    else:
        source_dir = Path(args.drive_root).expanduser() / args.folder_name
        source = find_latest_json(source_dir) if source_dir.exists() else None
        if source is None:
            icloud_dir = Path(args.icloud_manual_dir).expanduser()
            source = find_latest_json(icloud_dir) if icloud_dir.exists() else None
        if source is None:
            print(f"No JSON exports found under: {source_dir}")
            print(f"No JSON exports found under: {Path(args.icloud_manual_dir).expanduser()}")
            return 1

    if not source.exists():
        print(f"JSON export not found: {source}")
        return 1

    with source.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    result = ingest_payload(
        payload=payload,
        dest_csv=Path(args.dest_csv).expanduser(),
        raw_dir=Path(args.raw_dir).expanduser(),
        session_id=source.stem,
        sync_write=args.write,
    )
    print(f"Imported source: {source}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
