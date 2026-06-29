#!/usr/bin/env python3
"""Audit common macOS cleanup candidates without deleting anything."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Candidate:
    label: str
    path: str
    size_bytes: int
    risk: str
    action: str
    side_effect: str


def run_du(path: Path) -> int:
    if not path.exists() and not path.is_symlink():
        return 0
    try:
        out = subprocess.check_output(["du", "-sk", str(path)], text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0
    try:
        return int(out.split()[0]) * 1024
    except (IndexError, ValueError):
        return 0


def human_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def candidate(home: Path, rel: str, label: str, risk: str, action: str, side_effect: str) -> Candidate:
    path = home / rel
    return Candidate(label, str(path), run_du(path), risk, action, side_effect)


def top_children(path: Path, limit: int) -> list[Candidate]:
    if not path.exists() or not path.is_dir():
        return []
    rows = []
    for child in path.iterdir():
        if child.name in {".", ".."}:
            continue
        rows.append(
            Candidate(
                child.name,
                str(child),
                run_du(child),
                "inspect",
                "Review large children before deleting broad parent.",
                "Depends on owning app/tool.",
            )
        )
    rows.sort(key=lambda c: c.size_bytes, reverse=True)
    return rows[:limit]


def build_candidates(home: Path, fast: bool = False) -> list[Candidate]:
    safe = [
        ("Library/Logs/Unity", "Unity logs", "safe-ish", "Delete with Unity closed.", "Loses old Unity diagnostic logs."),
        ("Library/Logs", "All user logs", "safe-ish", "Delete selected large app log folders.", "Loses diagnostic history."),
        ("Movies/CapCut/User Data/Cache", "CapCut cache", "safe-ish", "Delete with CapCut closed.", "CapCut may rebuild cache."),
        (".cache/uv", "uv cache", "safe-ish", "Delete if package redownloads are acceptable.", "Future Python installs may redownload."),
        (".cache/whisper", "Whisper cache", "safe-ish", "Delete if model redownloads are acceptable.", "Transcription may redownload models."),
        (".cache/codex-runtimes", "Codex runtime cache", "safe-ish", "Delete if runtime redownloads are acceptable.", "Future runs may redownload runtimes."),
        (".npm", "npm cache", "safe-ish", "Prefer npm cache clean --force.", "Future npm installs may be slower."),
        ("Library/Caches/Homebrew", "Homebrew cache", "safe-ish", "Prefer brew cleanup --prune=all.", "Formula downloads may be gone."),
        ("Library/Caches/pip", "pip cache", "safe-ish", "Delete if package redownloads are acceptable.", "Future pip installs may be slower."),
        ("Library/Caches/ms-playwright", "Playwright cache", "safe-ish", "Delete if browser redownloads are acceptable.", "Tests may redownload browsers."),
        ("Library/Caches/ms-playwright-go", "Playwright Go cache", "safe-ish", "Delete if browser redownloads are acceptable.", "Tests may redownload browsers."),
        ("Library/Caches/huggingface-codex", "Hugging Face/Codex cache", "safe-ish", "Delete if model/cache redownloads are acceptable.", "Future runs may redownload cache files."),
        ("Library/Caches/pencil-updater", "Pencil updater cache", "safe-ish", "Delete when Pencil is not updating.", "Updater may redownload package data."),
        ("Library/Caches/com.google.antigravity.ShipIt", "Antigravity ShipIt cache", "safe-ish", "Delete when the app is closed.", "Updater may redownload package data."),
        ("Library/Caches/antigravity-updater", "Antigravity updater cache", "safe-ish", "Delete when the app is closed.", "Updater may redownload package data."),
        ("Library/Application Support/Caches", "Application Support caches", "safe-ish", "Delete selected cache children only.", "Apps may rebuild cache data."),
        (".Trash", "Trash", "safe-ish", "Empty only after user accepts permanent deletion.", "Deletes trashed files permanently."),
    ]
    broad = [
        ("Library/Caches", "All user caches", "safe-ish", "Prefer selected large children over broad wipe.", "Apps rebuild caches."),
        (".cache", "CLI/tool caches", "safe-ish", "Delete selected large children.", "Tools redownload/rebuild."),
    ]
    review = [
        ("Downloads", "Downloads", "review-first", "Review or archive manually.", "May contain user files."),
        ("Movies/CapCut/User Data/Projects", "CapCut projects", "review-first", "Archive old projects with symlinks; do not delete blindly.", "Deleting loses drafts/projects."),
        ("Library/Messages", "Messages", "review-first", "Clean through Messages/manual attachment review.", "May delete message history/attachments."),
        ("Library/Mail", "Mail", "review-first", "Clean through Mail/account settings.", "May affect local mail data/cache."),
        ("Library/Application Support/Notion", "Notion app data", "review-first", "Clean through app or accept re-sync risk.", "May force re-sync or lose local state."),
        ("Library/Application Support/Notion/Partitions", "Notion partition data", "review-first", "Review before deleting; prefer app controls or explicit re-sync acceptance.", "May force re-sync, lose local session/cache state, or break offline data."),
        ("Library/Application Support/Claude", "Claude app data", "review-first", "Avoid direct deletion unless app repair/redownload is acceptable.", "May force runtime repair/redownload."),
        ("Library/Application Support/Claude/vm_bundles", "Claude VM bundles", "review-first", "Review before deleting; only remove if runtime rebuild/redownload is acceptable.", "May force Claude runtime repair or redownload."),
        ("Library/Application Support/Cursor", "Cursor app data", "review-first", "Review caches vs User state before deleting.", "May lose IDE state/history."),
        ("Library/Application Support/Google/Chrome", "Chrome profile data", "review-first", "Clean through Chrome settings/profile review.", "May affect profiles, sessions, extensions, history."),
        ("Library/Application Support/Google/DriveFS", "Google DriveFS data", "review-first", "Clean through Google Drive settings or account controls.", "May affect sync cache and offline files."),
        ("Library/Developer/CoreSimulator", "CoreSimulator data", "review-first", "Prefer xcrun simctl delete unavailable; review before deleting devices.", "May remove simulator devices and app data."),
    ]
    rows = [candidate(home, *item) for item in safe + broad]
    if not fast:
        rows.extend(candidate(home, *item) for item in review)
    for path in sorted((home / "Library/Application Support").glob("app_shell_cache_*")):
        rows.append(
            Candidate(
                "App shell package cache",
                str(path),
                run_du(path),
                "safe-ish",
                "Delete the exact cache directory when the owning app is closed.",
                "Owning app may redownload package data.",
            )
        )
    rows = [row for row in rows if row.size_bytes > 0]
    rows.sort(key=lambda c: (c.risk != "safe-ish", -c.size_bytes))
    return rows


def print_table(rows: Iterable[Candidate]) -> None:
    print("Mac cleanup candidates (read-only)")
    print("----------------------------------")
    for row in rows:
        print(f"{human_size(row.size_bytes):>10}  {row.risk:<12}  {row.label}")
        print(f"            path: {row.path}")
        print(f"          action: {row.action}")
        print(f"     side-effect: {row.side_effect}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit common macOS cleanup candidates without deleting anything.")
    parser.add_argument("--home", default=str(Path.home()), help="Home directory to inspect. Defaults to current user home.")
    parser.add_argument("--top", type=int, default=12, help="Show this many largest children for broad cleanup folders.")
    parser.add_argument("--fast", action="store_true", help="Skip heavier review-first app-data scans for active freeze/no-restart triage.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    home = Path(args.home).expanduser().resolve()
    rows = build_candidates(home, fast=args.fast)

    top_sections = {
        "Library/Caches": top_children(home / "Library/Caches", args.top),
        "Library/Logs": top_children(home / "Library/Logs", args.top),
        ".cache": top_children(home / ".cache", args.top),
        "Downloads": top_children(home / "Downloads", args.top),
        "Library/Developer": top_children(home / "Library/Developer", args.top),
    }
    if not args.fast:
        top_sections["Library/Application Support"] = top_children(home / "Library/Application Support", args.top)

    if args.json:
        print(
            json.dumps(
                {
                    "home": str(home),
                    "candidates": [asdict(row) for row in rows],
                    "top_children": {key: [asdict(row) for row in value] for key, value in top_sections.items()},
                },
                indent=2,
            )
        )
        return 0

    print_table(rows)
    print()
    print("Largest children for inspection")
    print("-------------------------------")
    for section, children in top_sections.items():
        if not children:
            continue
        print(f"\n{section}")
        for child in children:
            print(f"  {human_size(child.size_bytes):>10}  {child.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
