#!/usr/bin/env python3
"""
Print health context for daily interview from canonical health metrics CSV.

Default date is yesterday, matching the daily workflow timing.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

from health_paths import daily_health_metrics_csv
from health_overnight_analysis import analyze_overnight, fmt_num, fmt_pct
from repo_paths import resolve_private_repo_root


ROOT = resolve_private_repo_root()
DEFAULT_HEALTH_CSV = daily_health_metrics_csv(ROOT)


def default_target_date() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def fmt(value: str, suffix: str = "") -> str:
    v = (value or "").strip()
    return f"{v}{suffix}" if v else "missing"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print daily health context for interview")
    parser.add_argument("--date", default=default_target_date(), help="Target date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--health-csv", default=str(DEFAULT_HEALTH_CSV), help="Canonical health CSV path")
    args = parser.parse_args()

    health_csv = Path(args.health_csv).expanduser()
    if not health_csv.exists():
        print(f"Health CSV not found: {health_csv}")
        return 1

    with health_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    row = next((r for r in rows if (r.get("date") or "").strip() == args.date), None)
    if not row:
        print(f"No health row found for {args.date}.")
        recent = [r.get("date", "") for r in rows[-5:] if r.get("date")]
        if recent:
            print("Recent available dates:", ", ".join(recent))
        return 1

    print(f"Health context for {args.date}:")
    print(f"- Sleep: {fmt(row.get('sleep_hours', ''), ' h')}")
    print(f"- Resting HR: {fmt(row.get('resting_hr', ''), ' bpm')}")
    print(f"- Blood glucose: {fmt(row.get('blood_glucose_mmol_l', ''), ' mmol/L')}")
    print(f"- Blood oxygen: {fmt(row.get('blood_oxygen_pct', ''), ' %')}")
    print(f"- Weight: {fmt(row.get('weight_kg', ''), ' kg')}")
    print(f"- Exercise: {fmt(row.get('exercise_minutes', ''), ' min')}")
    print(f"- Steps: {fmt(row.get('steps', ''))}")
    print(f"- Active energy: {fmt(row.get('active_energy_kcal', ''), ' kcal')}")
    print(f"- HRV: {fmt(row.get('hrv_ms', ''), ' ms')}")
    print(f"- Heart rate avg: {fmt(row.get('heart_rate_avg', ''), ' bpm')}")
    print(f"- Heart rate min: {fmt(row.get('heart_rate_min', ''), ' bpm')}")
    print(f"- Heart rate max: {fmt(row.get('heart_rate_max', ''), ' bpm')}")

    overnight = analyze_overnight(args.date)
    oxygen_stats = overnight["oxygen_stats"]
    hr_stats = overnight["heart_rate_stats"]
    print("- Overnight oxygen source:", overnight["source"])
    print(
        "- Overnight SpO2:"
        f" samples={oxygen_stats.get('count', 0)},"
        f" min={fmt_pct(oxygen_stats.get('min'))},"
        f" median={fmt_pct(oxygen_stats.get('median'))},"
        f" avg={fmt_pct(oxygen_stats.get('avg'))}"
    )
    if oxygen_stats.get("count", 0):
        print(
            "- Overnight low-SpO2 exposure:"
            f" <94={fmt_pct(oxygen_stats.get('below_94_pct'))},"
            f" <92={fmt_pct(oxygen_stats.get('below_92_pct'))},"
            f" <90={fmt_pct(oxygen_stats.get('below_90_pct'))}"
        )
    if hr_stats.get("count", 0):
        print(
            "- Overnight HR:"
            f" min={fmt_num(hr_stats.get('min'), 0, ' bpm')},"
            f" avg={fmt_num(hr_stats.get('avg'), 1, ' bpm')},"
            f" max={fmt_num(hr_stats.get('max'), 0, ' bpm')}"
        )
    print(f"- Overnight status: {overnight['severity']}")
    for finding in overnight["findings"]:
        print(f"  - {finding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
