#!/usr/bin/env python3
"""
Legacy helper for older journal setups that copied health data into
journal/daily_metrics.csv.

The current workflow keeps health telemetry in
health-data/records/daily_health_metrics.csv and leaves
journal/daily_metrics.csv for subjective / productivity metrics only.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from health_paths import daily_health_metrics_csv
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
DEFAULT_HEALTH_CSV = daily_health_metrics_csv(ROOT)
DEFAULT_DAILY_METRICS = ROOT / "journal" / "daily_metrics.csv"


@dataclass
class RowUpdate:
    date: str
    old_sleep: str
    new_sleep: str
    old_exercise: str
    new_exercise: str


def normalize_number(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    try:
        number = float(v)
        if number.is_integer():
            return str(int(number))
        return str(number)
    except ValueError:
        return v


def load_health_map(health_csv: Path) -> dict[str, dict[str, str]]:
    with health_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"date", "sleep_hours", "exercise_minutes"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"health CSV missing required columns. Required: {sorted(required)}. "
                f"Found: {reader.fieldnames}"
            )
        out: dict[str, dict[str, str]] = {}
        for row in reader:
            date = (row.get("date") or "").strip()
            if not date:
                continue
            out[date] = {
                "sleep": normalize_number(row.get("sleep_hours", "")),
                "exercise": normalize_number(row.get("exercise_minutes", "")),
            }
        return out


def sync_metrics(
    daily_metrics_csv: Path,
    health_map: dict[str, dict[str, str]],
    write: bool,
    fill_only_blanks: bool,
) -> tuple[list[RowUpdate], int]:
    with daily_metrics_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [f for f in list(reader.fieldnames or []) if f is not None]
        rows = []
        for row in reader:
            if None in row:
                row.pop(None, None)
            rows.append(row)

    sleep_col = "Sleep (hours)"
    exercise_col = "Exercise (minutes)"
    date_col = "Date"

    for col in [date_col, sleep_col, exercise_col]:
        if col not in fieldnames:
            raise ValueError(f"daily metrics CSV missing required column: {col}")

    updates: list[RowUpdate] = []
    rows_seen = 0

    for row in rows:
        rows_seen += 1
        date = (row.get(date_col) or "").strip()
        if date not in health_map:
            continue
        incoming_sleep = health_map[date]["sleep"]
        incoming_exercise = health_map[date]["exercise"]
        old_sleep = (row.get(sleep_col) or "").strip()
        old_exercise = (row.get(exercise_col) or "").strip()

        new_sleep = old_sleep
        new_exercise = old_exercise

        if incoming_sleep and (not fill_only_blanks or not old_sleep):
            new_sleep = incoming_sleep
        if incoming_exercise and (not fill_only_blanks or not old_exercise):
            new_exercise = incoming_exercise

        if new_sleep != old_sleep or new_exercise != old_exercise:
            row[sleep_col] = new_sleep
            row[exercise_col] = new_exercise
            updates.append(
                RowUpdate(
                    date=date,
                    old_sleep=old_sleep,
                    new_sleep=new_sleep,
                    old_exercise=old_exercise,
                    new_exercise=new_exercise,
                )
            )

    if write and updates:
        with daily_metrics_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return updates, rows_seen


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy sync helper for older daily_metrics.csv layouts")
    parser.add_argument("--health-csv", default=str(DEFAULT_HEALTH_CSV), help="Path to health shortcut CSV")
    parser.add_argument("--daily-metrics-csv", default=str(DEFAULT_DAILY_METRICS), help="Path to daily_metrics.csv")
    parser.add_argument("--write", action="store_true", help="Write changes. Without this, run in dry-run mode.")
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="By default only fill blank sleep/exercise cells. Set this to overwrite existing values.",
    )
    args = parser.parse_args()

    print("This script is legacy.")
    print("Current workflow keeps health data in the canonical health records CSV.")
    print("and no longer syncs sleep/exercise into journal/daily_metrics.csv by default.")
    print("No changes applied.")
    return 0

    health_csv = Path(args.health_csv)
    daily_metrics_csv = Path(args.daily_metrics_csv)

    if not health_csv.exists():
        print(f"Health CSV not found: {health_csv}")
        print("Create iOS Shortcut export first, then run again.")
        return 1
    if not daily_metrics_csv.exists():
        print(f"Daily metrics CSV not found: {daily_metrics_csv}")
        return 1

    health_map = load_health_map(health_csv)
    updates, total_rows = sync_metrics(
        daily_metrics_csv=daily_metrics_csv,
        health_map=health_map,
        write=args.write,
        fill_only_blanks=not args.overwrite_existing,
    )

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"[{mode}] scanned {total_rows} daily_metrics rows; health days available: {len(health_map)}")
    if not updates:
        print("No changes needed.")
        return 0

    print(f"Planned updates: {len(updates)}")
    for u in updates[:40]:
        print(
            f"- {u.date}: sleep '{u.old_sleep}' -> '{u.new_sleep}', "
            f"exercise '{u.old_exercise}' -> '{u.new_exercise}'"
        )
    if len(updates) > 40:
        print(f"... and {len(updates) - 40} more")

    if not args.write:
        print("Dry-run only. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
