#!/usr/bin/env python3
"""Read one indexed ZIP member directly from Google Drive on demand."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import zipfile
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession

from inventory_google_drive_zips import DriveRangeReader, load_credentials


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--member", required=True, help="Exact member path")
    parser.add_argument("--archive", help="Archive name when a path is duplicated")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output", type=Path, help="Extract atomically to this path")
    output.add_argument(
        "--stdout",
        action="store_true",
        help="Write a bounded preview to stdout instead of persisting it",
    )
    parser.add_argument(
        "--head-bytes", type=int, default=65536, help="Maximum bytes for --stdout"
    )
    args = parser.parse_args()

    with gzip.open(args.inventory.expanduser(), "rt", encoding="utf-8") as handle:
        inventory = json.load(handle)

    matches = []
    for archive in inventory["archives"]:
        if args.archive and archive["name"] != args.archive:
            continue
        for member in archive["members"]:
            if member["path"] == args.member:
                matches.append((archive, member))

    if not matches:
        raise RuntimeError(f"Member not found in inventory: {args.member}")
    if len(matches) > 1:
        names = ", ".join(archive["name"] for archive, _ in matches)
        raise RuntimeError(f"Member exists in multiple archives; pass --archive: {names}")

    archive, member = matches[0]
    session = AuthorizedSession(load_credentials(args.token.expanduser()))
    reader = DriveRangeReader(session, archive["id"], int(archive["archive_bytes"]))
    print(
        f"Archive: {archive['name']}\nMember: {member['path']}\n"
        f"Uncompressed: {member['uncompressed_bytes']} bytes",
        file=sys.stderr,
    )

    with zipfile.ZipFile(reader) as package, package.open(args.member) as source:
        if args.output:
            target = args.output.expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(target.suffix + ".part")
            with partial.open("wb") as destination:
                while chunk := source.read(8 * 1024 * 1024):
                    destination.write(chunk)
            os.replace(partial, target)
            print(f"Output: {target}", file=sys.stderr)
        elif args.stdout:
            sys.stdout.buffer.write(source.read(max(0, args.head_bytes)))
        else:
            print("Pass --stdout for a bounded preview or --output to extract.")

    print(f"Range bytes fetched: {reader.bytes_fetched}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
