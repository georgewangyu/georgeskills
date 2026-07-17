#!/usr/bin/env python3
"""Download a bounded Google Drive folder into a verified local archive.

The downloader uses a dedicated Drive read-only OAuth token, writes through a
``.part`` file, resumes interrupted transfers with HTTP Range requests, checks
the expected byte count, and records progress in an atomic JSON manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
API_MEDIA_URL = "https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
CHUNK_SIZE = 8 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_filename(name: str, file_id: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f/:]", "_", name).strip().strip(".")
    return cleaned or f"drive-file-{file_id}"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def load_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    credentials: Credentials | None = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        credentials = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    os.chmod(token_path, 0o600)
    return credentials


def list_folder_files(service: Any, folder_id: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields=(
                    "nextPageToken,files(id,name,mimeType,size,createdTime,modifiedTime,md5Checksum)"
                ),
                pageSize=1000,
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


def build_manifest(
    service: Any,
    folder_id: str,
    created_date: str | None,
    account_email: str,
) -> dict[str, Any]:
    files = list_folder_files(service, folder_id)
    if created_date:
        files = [item for item in files if item.get("createdTime", "")[:10] == created_date]

    entries = []
    for item in sorted(files, key=lambda row: row.get("name", "")):
        entries.append(
            {
                "id": item["id"],
                "name": item["name"],
                "mime_type": item.get("mimeType"),
                "size": int(item["size"]) if item.get("size") else None,
                "created_time": item.get("createdTime"),
                "modified_time": item.get("modifiedTime"),
                "drive_md5": item.get("md5Checksum"),
                "status": "pending",
            }
        )

    return {
        "schema": "google-drive-archive-manifest-v1",
        "generated_at": utc_now(),
        "account": account_email,
        "folder_id": folder_id,
        "created_date_filter": created_date,
        "files": entries,
    }


def pending_bytes(manifest: dict[str, Any], output_dir: Path) -> int:
    total = 0
    for entry in manifest["files"]:
        expected = entry.get("size")
        if expected is None:
            continue
        target = output_dir / safe_filename(entry["name"], entry["id"])
        present = target.stat().st_size if target.exists() else 0
        total += max(0, int(expected) - present)
    return total


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def download_entry(
    session: AuthorizedSession,
    entry: dict[str, Any],
    output_dir: Path,
    checksum: bool,
) -> None:
    target = output_dir / safe_filename(entry["name"], entry["id"])
    partial = target.with_suffix(target.suffix + ".part")
    expected = entry.get("size")

    if target.exists() and expected is not None and target.stat().st_size == expected:
        entry["status"] = "verified"
        entry["local_path"] = target.name
        entry["verified_size"] = target.stat().st_size
        if checksum and not entry.get("sha256"):
            entry["sha256"] = sha256_file(target)
        entry["verified_at"] = utc_now()
        return

    start = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={start}-"} if start else {}
    response = session.get(
        API_MEDIA_URL.format(file_id=entry["id"]), headers=headers, stream=True
    )
    if start and response.status_code == 200:
        start = 0
        partial.unlink(missing_ok=True)
    elif start and response.status_code != 206:
        response.raise_for_status()
    else:
        response.raise_for_status()

    mode = "ab" if start else "wb"
    entry["status"] = "downloading"
    entry["started_at"] = entry.get("started_at") or utc_now()
    with partial.open(mode) as handle:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                handle.write(chunk)

    actual = partial.stat().st_size
    if expected is not None and actual != expected:
        raise RuntimeError(
            f"Size mismatch for {entry['name']}: expected {expected}, received {actual}"
        )

    os.replace(partial, target)
    entry["status"] = "verified"
    entry["local_path"] = target.name
    entry["verified_size"] = target.stat().st_size
    if checksum:
        entry["sha256"] = sha256_file(target)
    entry["verified_at"] = utc_now()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--folder-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--account", help="Fail if OAuth resolves to another account")
    parser.add_argument("--created-date", help="UTC date filter in YYYY-MM-DD format")
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--no-checksum", action="store_true")
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--file-id", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    credentials = load_credentials(args.credentials.expanduser(), args.token.expanduser())
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    account = service.about().get(fields="user(emailAddress)").execute()["user"][
        "emailAddress"
    ]
    if args.account and account.lower() != args.account.lower():
        raise RuntimeError(f"Authenticated as {account}; expected {args.account}")

    manifest_path = args.manifest.expanduser()
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("folder_id") != args.folder_id:
            raise RuntimeError("Existing manifest belongs to a different Drive folder")
    else:
        manifest = build_manifest(service, args.folder_id, args.created_date, account)
        atomic_write_json(manifest_path, manifest)

    selected = manifest["files"]
    if args.file_id:
        wanted = set(args.file_id)
        selected = [entry for entry in selected if entry["id"] in wanted]
    if args.max_files is not None:
        selected = selected[: args.max_files]

    total = sum(int(entry.get("size") or 0) for entry in selected)
    print(f"Account: {account}")
    print(f"Selected: {len(selected)} files / {total / (1024 ** 3):.2f} GiB")
    print(f"Manifest: {manifest_path}")
    if args.list_only:
        return 0

    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    needed = pending_bytes({"files": selected}, output_dir)
    free = shutil.disk_usage(output_dir).free
    headroom = 5 * 1024**3
    if free < needed + headroom:
        raise RuntimeError(
            f"Insufficient free space: need {needed / 1024**3:.2f} GiB plus "
            f"5 GiB headroom, have {free / 1024**3:.2f} GiB"
        )

    session = AuthorizedSession(credentials)
    for index, entry in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}] {entry['name']}", flush=True)
        try:
            download_entry(session, entry, output_dir, not args.no_checksum)
        except Exception as error:
            entry["status"] = "error"
            entry["error"] = str(error)
            entry["updated_at"] = utc_now()
            atomic_write_json(manifest_path, manifest)
            raise
        atomic_write_json(manifest_path, manifest)

    verified = sum(entry.get("status") == "verified" for entry in selected)
    print(f"Verified: {verified}/{len(selected)} files")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted; rerun the same command to resume.", file=sys.stderr)
        raise SystemExit(130)
