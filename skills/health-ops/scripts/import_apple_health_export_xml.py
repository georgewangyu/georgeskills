#!/usr/bin/env python3
"""
Import one day of metrics from Apple Health export.xml into canonical health CSV.

Default target date is yesterday (local date), matching daily workflow timing.
"""

from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from health_paths import apple_health_export_xml, daily_health_metrics_csv
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
DEFAULT_EXPORT_XML = apple_health_export_xml(ROOT)
DEFAULT_DEST = daily_health_metrics_csv(ROOT)


SLEEP_ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
}


@dataclass
class DayAgg:
    sleep_seconds: float = 0.0
    steps: float = 0.0
    exercise_minutes: float = 0.0
    active_energy_kcal: float = 0.0
    resting_hr_sum: float = 0.0
    resting_hr_count: int = 0
    hrv_ms_sum: float = 0.0
    hrv_ms_count: int = 0
    blood_glucose_mmol_sum: float = 0.0
    blood_glucose_mmol_count: int = 0


def target_day_default() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def day_bounds(day_text: str) -> tuple[datetime, datetime]:
    d = date.fromisoformat(day_text)
    start = datetime.combine(d, time.min).astimezone()
    end = start + timedelta(days=1)
    return start, end


def overlap_seconds(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> float:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end <= start:
        return 0.0
    return (end - start).total_seconds()


def to_kcal(value: float, unit: str) -> float:
    u = (unit or "").strip().lower()
    if "kcal" in u or "cal" in u:
        return value
    if "kj" in u:
        return value / 4.184
    if u == "j":
        return value / 4184.0
    return value


def to_mmol_l_glucose(value: float, unit: str) -> float:
    u = (unit or "").strip().lower()
    if "mmol/l" in u:
        return value
    if "mg/dl" in u:
        return value * 0.0555
    return value


def to_ms(value: float, unit: str) -> float:
    u = (unit or "").strip().lower()
    if u == "s":
        return value * 1000.0
    return value


def within_day(ts: datetime, day_start: datetime, day_end: datetime) -> bool:
    return day_start <= ts < day_end


def collect_day_metrics(export_xml: Path, target_date: str) -> DayAgg:
    day_start, day_end = day_bounds(target_date)
    agg = DayAgg()

    context = ET.iterparse(export_xml, events=("end",))
    for _event, elem in context:
        if elem.tag != "Record":
            continue

        record_type = elem.attrib.get("type", "")
        start_raw = elem.attrib.get("startDate")
        end_raw = elem.attrib.get("endDate")
        value_raw = elem.attrib.get("value")
        unit = elem.attrib.get("unit", "")

        try:
            start_dt = parse_dt(start_raw) if start_raw else None
            end_dt = parse_dt(end_raw) if end_raw else None
        except Exception:
            elem.clear()
            continue

        if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
            if value_raw in SLEEP_ASLEEP_VALUES and start_dt and end_dt:
                agg.sleep_seconds += overlap_seconds(start_dt, end_dt, day_start, day_end)
            elem.clear()
            continue

        if not start_dt or not within_day(start_dt, day_start, day_end):
            elem.clear()
            continue

        value = to_float(value_raw)
        if value is None:
            elem.clear()
            continue

        if record_type == "HKQuantityTypeIdentifierStepCount":
            agg.steps += value
        elif record_type == "HKQuantityTypeIdentifierAppleExerciseTime":
            agg.exercise_minutes += value
        elif record_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
            agg.active_energy_kcal += to_kcal(value, unit)
        elif record_type == "HKQuantityTypeIdentifierRestingHeartRate":
            agg.resting_hr_sum += value
            agg.resting_hr_count += 1
        elif record_type == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":
            agg.hrv_ms_sum += to_ms(value, unit)
            agg.hrv_ms_count += 1
        elif record_type == "HKQuantityTypeIdentifierBloodGlucose":
            agg.blood_glucose_mmol_sum += to_mmol_l_glucose(value, unit)
            agg.blood_glucose_mmol_count += 1

        elem.clear()

    return agg


def fmt_num(v: float | None, decimals: int = 3) -> str:
    if v is None:
        return ""
    if abs(v - int(v)) < 1e-9:
        return str(int(v))
    return f"{v:.{decimals}f}".rstrip("0").rstrip(".")


def upsert_canonical(dest: Path, target_date: str, agg: DayAgg) -> None:
    header = [
        "date",
        "sleep_hours",
        "steps",
        "exercise_minutes",
        "active_energy_kcal",
        "resting_hr",
        "hrv_ms",
        "blood_glucose_mmol_l",
    ]

    row = {
        "date": target_date,
        "sleep_hours": fmt_num(agg.sleep_seconds / 3600.0 if agg.sleep_seconds > 0 else None),
        "steps": fmt_num(agg.steps if agg.steps > 0 else None, decimals=0),
        "exercise_minutes": fmt_num(agg.exercise_minutes if agg.exercise_minutes > 0 else None, decimals=1),
        "active_energy_kcal": fmt_num(agg.active_energy_kcal if agg.active_energy_kcal > 0 else None),
        "resting_hr": fmt_num(agg.resting_hr_sum / agg.resting_hr_count if agg.resting_hr_count else None),
        "hrv_ms": fmt_num(agg.hrv_ms_sum / agg.hrv_ms_count if agg.hrv_ms_count else None),
        "blood_glucose_mmol_l": fmt_num(
            agg.blood_glucose_mmol_sum / agg.blood_glucose_mmol_count if agg.blood_glucose_mmol_count else None
        ),
    }

    rows: list[dict[str, str]] = []
    if dest.exists():
        with dest.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    replaced = False
    for r in rows:
        if r.get("date") == target_date:
            for k in header:
                r[k] = row.get(k, "")
            replaced = True
            break

    if not replaced:
        rows.append(row)
        rows.sort(key=lambda r: r.get("date", ""))

    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import daily metrics from Apple Health export.xml")
    parser.add_argument("--date", default=target_day_default(), help="Target date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--export-xml", default=str(DEFAULT_EXPORT_XML), help="Path to Apple Health export.xml")
    parser.add_argument("--dest-csv", default=str(DEFAULT_DEST), help="Canonical destination CSV")
    args = parser.parse_args()

    export_xml = Path(args.export_xml).expanduser()
    dest = Path(args.dest_csv).expanduser()
    if not export_xml.exists():
        print(f"export.xml not found: {export_xml}")
        return 1

    agg = collect_day_metrics(export_xml, args.date)
    upsert_canonical(dest, args.date, agg)

    print(f"Imported Apple Health XML for {args.date}")
    print(f"Wrote: {dest}")
    print(
        "Values -> "
        f"sleep_hours={fmt_num(agg.sleep_seconds / 3600.0 if agg.sleep_seconds > 0 else None)}, "
        f"resting_hr={fmt_num(agg.resting_hr_sum / agg.resting_hr_count if agg.resting_hr_count else None)}, "
        f"blood_glucose_mmol_l={fmt_num(agg.blood_glucose_mmol_sum / agg.blood_glucose_mmol_count if agg.blood_glucose_mmol_count else None)}, "
        f"exercise_minutes={fmt_num(agg.exercise_minutes if agg.exercise_minutes > 0 else None, decimals=1)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
