#!/usr/bin/env python3
"""Inventory ZIP members in Google Drive without downloading whole archives."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
API_MEDIA_URL = "https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
MAX_FALLBACK_CACHE = 128 * 1024 * 1024


class DriveRangeReader(io.RawIOBase):
    """Seekable read-only view backed by Drive HTTP Range requests."""

    def __init__(self, session: AuthorizedSession, file_id: str, size: int):
        self.session = session
        self.url = API_MEDIA_URL.format(file_id=file_id)
        self.size = size
        self.position = 0
        self.bytes_fetched = 0
        self.full_payload: bytes | None = None

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self.position + offset
        elif whence == io.SEEK_END:
            position = self.size + offset
        else:
            raise ValueError(f"Unsupported whence: {whence}")
        if position < 0:
            raise ValueError("Negative seek position")
        self.position = min(position, self.size)
        return self.position

    def read(self, size: int = -1) -> bytes:
        if self.position >= self.size:
            return b""
        end = self.size - 1 if size is None or size < 0 else min(
            self.size - 1, self.position + size - 1
        )
        start = self.position
        if self.full_payload is not None:
            payload = self.full_payload[start : end + 1]
            self.position += len(payload)
            return payload
        response = self.session.get(
            self.url,
            headers={"Range": f"bytes={start}-{end}"},
            timeout=120,
            stream=True,
        )
        response.raise_for_status()
        if response.status_code == 200:
            if self.size > MAX_FALLBACK_CACHE:
                response.close()
                raise IOError(
                    "Drive ignored a Range request for an archive larger than "
                    f"{MAX_FALLBACK_CACHE / 1024**2:.0f} MiB; refusing full download"
                )
            full_payload = response.content
            if len(full_payload) != self.size:
                raise IOError(
                    f"Full response mismatch: expected {self.size}, received "
                    f"{len(full_payload)}"
                )
            self.full_payload = full_payload
            self.bytes_fetched += len(full_payload)
            payload = full_payload[start : end + 1]
        else:
            payload = response.content
            self.bytes_fetched += len(payload)
        expected = end - start + 1
        if len(payload) != expected:
            raise IOError(
                f"Range response mismatch: requested {expected} bytes, received {len(payload)}"
            )
        self.position += len(payload)
        return payload


def load_credentials(token_path: Path) -> Credentials:
    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        os.chmod(token_path, 0o600)
    if not credentials.valid:
        raise RuntimeError("Drive read-only token is invalid; authorize it again")
    return credentials


def product_name(member_name: str) -> str:
    parts = member_name.replace("\\", "/").split("/")
    if parts and parts[0].lower() == "takeout" and len(parts) > 1:
        return parts[1] or "(root)"
    return parts[0] or "(root)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-zips", type=int)
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archives = [
        item for item in manifest["files"] if item["name"].lower().endswith(".zip")
    ]
    if args.max_zips is not None:
        archives = archives[: args.max_zips]

    session = AuthorizedSession(load_credentials(args.token.expanduser()))
    result: dict[str, Any] = {
        "schema": "google-drive-remote-zip-inventory-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(manifest_path),
        "archives": [],
    }

    for index, archive in enumerate(archives, start=1):
        print(f"[{index}/{len(archives)}] {archive['name']}", flush=True)
        reader = DriveRangeReader(session, archive["id"], int(archive["size"]))
        products: dict[str, dict[str, int]] = defaultdict(
            lambda: {"members": 0, "uncompressed_bytes": 0, "compressed_bytes": 0}
        )
        members = []
        try:
            with zipfile.ZipFile(reader) as package:
                for info in package.infolist():
                    product = product_name(info.filename)
                    products[product]["members"] += 1
                    products[product]["uncompressed_bytes"] += info.file_size
                    products[product]["compressed_bytes"] += info.compress_size
                    members.append(
                        {
                            "path": info.filename,
                            "uncompressed_bytes": info.file_size,
                            "compressed_bytes": info.compress_size,
                            "crc32": f"{info.CRC:08x}",
                        }
                    )
            status = "indexed"
            error = None
        except (zipfile.BadZipFile, IOError, OSError) as exc:
            status = "error"
            error = str(exc)

        result["archives"].append(
            {
                "id": archive["id"],
                "name": archive["name"],
                "archive_bytes": int(archive["size"]),
                "status": status,
                "error": error,
                "range_bytes_fetched": reader.bytes_fetched,
                "products": dict(sorted(products.items())),
                "members": members,
            }
        )

    output = args.output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, output)

    total_members = sum(len(item["members"]) for item in result["archives"])
    fetched = sum(item["range_bytes_fetched"] for item in result["archives"])
    print(f"Indexed {total_members:,} members; fetched {fetched / 1024**2:.2f} MiB")
    print(f"Inventory: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
