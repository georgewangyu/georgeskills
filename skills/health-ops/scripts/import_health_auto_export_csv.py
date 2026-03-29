#!/usr/bin/env python3
"""
Import Health Auto Export aggregate CSV into the canonical health metrics CSV.

Source CSV example:
  health-data/source-records/HealthAutoExport_YYYYMMDDHHMMSS/HealthAutoExport-*.csv

Canonical destination:
  health-data/records/daily_health_metrics.csv

Output columns:
  date,sleep_hours,steps,exercise_minutes,active_energy_kcal,resting_hr,hrv_ms,blood_glucose_mmol_l
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path

from health_paths import daily_health_metrics_csv, resolve_health_source_records_root
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
HEALTH_OPS_DIR = Path(__file__).resolve().parent
DEFAULT_EXPORTS_ROOT = resolve_health_source_records_root(ROOT)
DEFAULT_DEST = daily_health_metrics_csv(ROOT)
SYNC_SCRIPT = HEALTH_OPS_DIR / "sync_health_shortcut_metrics.py"


@dataclass
class CanonicalRow:
    date: str
    sleep_hours: str
    steps: str
    exercise_minutes: str
    active_energy_kcal: str
    resting_hr: str
    hrv_ms: str
    blood_glucose_mmol_l: str


def latest_export_csv(exports_root: Path) -> Path | None:
    candidates = sorted(
        exports_root.glob("HealthAutoExport_*/HealthAutoExport-*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def normalize_number(value: str, decimals: int = 2) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    try:
        n = float(v)
    except ValueError:
        return ""
    if n.is_integer():
        return str(int(n))
    return f"{n:.{decimals}f}".rstrip("0").rstrip(".")


def to_date(date_time_value: str) -> str:
    # Health Auto Export daily rows are typically "YYYY-MM-DD HH:MM:SS".
    return (date_time_value or "").strip().split(" ")[0]


def load_rows(source_csv: Path) -> list[CanonicalRow]:
    with source_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "Date/Time",
            "Sleep Analysis [Asleep] (hr)",
            "Step Count (count)",
            "Apple Exercise Time (min)",
            "Active Energy (kJ)",
            "Resting Heart Rate (count/min)",
            "Heart Rate Variability (ms)",
        }
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(
                "Health Auto Export CSV missing required columns: "
                + ", ".join(missing)
            )

        per_day: dict[str, CanonicalRow] = {}
        for row in reader:
            date = to_date(row.get("Date/Time", ""))
            if not date:
                continue

            active_energy_kj = normalize_number(row.get("Active Energy (kJ)", ""))
            active_energy_kcal = ""
            if active_energy_kj:
                active_energy_kcal = normalize_number(str(float(active_energy_kj) / 4.184))

            per_day[date] = CanonicalRow(
                date=date,
                sleep_hours=normalize_number(row.get("Sleep Analysis [Asleep] (hr)", ""), decimals=3),
                steps=normalize_number(row.get("Step Count (count)", ""), decimals=0),
                exercise_minutes=normalize_number(row.get("Apple Exercise Time (min)", ""), decimals=0),
                active_energy_kcal=active_energy_kcal,
                resting_hr=normalize_number(row.get("Resting Heart Rate (count/min)", ""), decimals=2),
                hrv_ms=normalize_number(row.get("Heart Rate Variability (ms)", ""), decimals=2),
                blood_glucose_mmol_l=normalize_number(row.get("Blood Glucose (mmol/L)", ""), decimals=3),
            )

    return [per_day[d] for d in sorted(per_day.keys())]


def write_canonical_csv(rows: list[CanonicalRow], dest_csv: Path) -> None:
    dest_csv.parent.mkdir(parents=True, exist_ok=True)
    with dest_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "date",
                "sleep_hours",
                "steps",
                "exercise_minutes",
                "active_energy_kcal",
                "resting_hr",
                "hrv_ms",
                "blood_glucose_mmol_l",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.date,
                    r.sleep_hours,
                    r.steps,
                    r.exercise_minutes,
                    r.active_energy_kcal,
                    r.resting_hr,
                    r.hrv_ms,
                    r.blood_glucose_mmol_l,
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Health Auto Export CSV into canonical daily_health_metrics.csv"
    )
    parser.add_argument(
        "--exports-root",
        default=str(DEFAULT_EXPORTS_ROOT),
        help="Path containing HealthAutoExport_* folders",
    )
    parser.add_argument(
        "--source-csv",
        default="",
        help="Explicit HealthAutoExport-*.csv path (overrides --exports-root latest pick)",
    )
    parser.add_argument(
        "--dest-csv",
        default=str(DEFAULT_DEST),
        help="Destination canonical health metrics CSV",
    )
    parser.add_argument(
        "--sync-daily-metrics",
        action="store_true",
        help="After import, run sync_health_shortcut_metrics.py",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="When used with --sync-daily-metrics, apply updates to journal/daily_metrics.csv",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="When syncing, overwrite existing sleep/exercise values instead of only filling blanks",
    )
    args = parser.parse_args()

    source_csv = Path(args.source_csv).expanduser() if args.source_csv else None
    if source_csv is None:
        exports_root = Path(args.exports_root).expanduser()
        source_csv = latest_export_csv(exports_root)
        if source_csv is None:
            print(f"No HealthAutoExport-*.csv found under: {exports_root}")
            print(
                "Note: AutoSync .hae files are proprietary. Use Health Auto Export "
                "aggregate CSV export for ingestion."
            )
            return 1

    if not source_csv.exists():
        print(f"Source CSV not found: {source_csv}")
        return 1

    dest_csv = Path(args.dest_csv).expanduser()
    rows = load_rows(source_csv)
    write_canonical_csv(rows, dest_csv)
    print(f"Imported {len(rows)} daily rows")
    print(f"Source: {source_csv}")
    print(f"Wrote:  {dest_csv}")

    if not args.sync_daily_metrics:
        return 0

    cmd = [
        "python3",
        str(SYNC_SCRIPT),
        "--health-csv",
        str(dest_csv),
    ]
    if args.write:
        cmd.append("--write")
    if args.overwrite_existing:
        cmd.append("--overwrite-existing")
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
