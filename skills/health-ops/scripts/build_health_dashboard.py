#!/usr/bin/env python3
"""
Build a health dashboard from Apple Health history plus recent daily sync files.

Outputs:
- journal/trends/health_dashboard.html
- journal/trends/health_dashboard_assets/*.svg
- journal/trends/health_dashboard_summary.json
"""

from __future__ import annotations

import argparse
import io
import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from health_paths import apple_health_export_xml, health_auto_export_raw_dir
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
EXPORT_XML = apple_health_export_xml(ROOT)
RAW_JSON_DIR = health_auto_export_raw_dir(ROOT)
TRENDS_DIR = ROOT / "journal" / "trends"
ASSETS_DIR = TRENDS_DIR / "health_dashboard_assets"
OUTPUT_HTML = TRENDS_DIR / "health_dashboard.html"
OUTPUT_SUMMARY = TRENDS_DIR / "health_dashboard_summary.json"

SLEEP_ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
}

METRIC_META = {
    "sleep_hours": {"label": "Sleep", "unit": "h", "decimals": 2, "good_direction": "up"},
    "steps": {"label": "Steps", "unit": "", "decimals": 0, "good_direction": "up"},
    "exercise_minutes": {"label": "Exercise", "unit": "min", "decimals": 0, "good_direction": "up"},
    "active_energy_kcal": {"label": "Active Energy", "unit": "kcal", "decimals": 0, "good_direction": "up"},
    "resting_hr": {"label": "Resting HR", "unit": "bpm", "decimals": 1, "good_direction": "down"},
    "hrv_ms": {"label": "HRV", "unit": "ms", "decimals": 1, "good_direction": "up"},
    "blood_oxygen_pct": {"label": "Blood Oxygen", "unit": "%", "decimals": 1, "good_direction": "up"},
    "weight_kg": {"label": "Weight", "unit": "kg", "decimals": 1, "good_direction": "down"},
    "heart_rate_avg": {"label": "Avg HR", "unit": "bpm", "decimals": 1, "good_direction": "down"},
    "heart_rate_min": {"label": "Min HR", "unit": "bpm", "decimals": 0, "good_direction": "down"},
    "heart_rate_max": {"label": "Max HR", "unit": "bpm", "decimals": 0, "good_direction": "down"},
}

CHART_COLORS = {
    "sleep_hours": "#1d4ed8",
    "steps": "#0f766e",
    "exercise_minutes": "#ea580c",
    "active_energy_kcal": "#dc2626",
    "resting_hr": "#7c3aed",
    "hrv_ms": "#0284c7",
    "blood_oxygen_pct": "#16a34a",
    "weight_kg": "#b45309",
    "heart_rate_avg": "#be123c",
}

XML_RECORD_TO_FIELD = {
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierAppleExerciseTime": "exercise_minutes",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy_kcal",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv_ms",
    "HKQuantityTypeIdentifierOxygenSaturation": "blood_oxygen_pct",
    "HKQuantityTypeIdentifierBodyMass": "weight_kg",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate_avg",
    "HKQuantityTypeIdentifierBloodGlucose": "blood_glucose_mmol_l",
}

JSON_METRIC_TO_FIELD = {
    "sleep analysis": "sleep_hours",
    "step count": "steps",
    "apple exercise time": "exercise_minutes",
    "active energy": "active_energy_kcal",
    "resting heart rate": "resting_hr",
    "heart rate variability": "hrv_ms",
    "heart rate variability sdnn": "hrv_ms",
    "blood oxygen saturation": "blood_oxygen_pct",
    "oxygen saturation": "blood_oxygen_pct",
    "body mass": "weight_kg",
    "weight body mass": "weight_kg",
    "heart rate": "heart_rate_avg",
    "blood glucose": "blood_glucose_mmol_l",
}


@dataclass
class DailyAccumulator:
    sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    avg_sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    avg_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    mins: dict[str, float] = field(default_factory=dict)
    maxs: dict[str, float] = field(default_factory=dict)
    lasts: dict[str, float] = field(default_factory=dict)

    def add_sum(self, field_name: str, value: float) -> None:
        self.sums[field_name] += value

    def add_avg(self, field_name: str, value: float) -> None:
        self.avg_sums[field_name] += value
        self.avg_counts[field_name] += 1

    def add_min(self, field_name: str, value: float) -> None:
        current = self.mins.get(field_name)
        self.mins[field_name] = value if current is None else min(current, value)

    def add_max(self, field_name: str, value: float) -> None:
        current = self.maxs.get(field_name)
        self.maxs[field_name] = value if current is None else max(current, value)

    def set_last(self, field_name: str, value: float) -> None:
        self.lasts[field_name] = value

    def as_row(self, date_str: str) -> dict[str, float | str]:
        row: dict[str, float | str] = {"date": date_str}
        for field_name, value in self.sums.items():
            row[field_name] = value
        for field_name, total in self.avg_sums.items():
            count = self.avg_counts.get(field_name, 0)
            if count:
                row[field_name] = total / count
        for field_name, value in self.mins.items():
            row[field_name] = value
        for field_name, value in self.maxs.items():
            row[field_name] = value
        for field_name, value in self.lasts.items():
            row[field_name] = value
        return row


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def normalize_name(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("_", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("%", " pct ")
    return " ".join(normalized.split())


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", ""))
        except ValueError:
            return None
    return None


def to_kcal(value: float, unit: str) -> float:
    lower = (unit or "").lower()
    if "kj" in lower:
        return value / 4.184
    if lower == "j":
        return value / 4184.0
    return value


def to_hours(value: float, unit: str) -> float:
    lower = (unit or "").lower()
    if "sec" in lower:
        return value / 3600.0
    if "min" in lower:
        return value / 60.0
    return value


def to_ms(value: float, unit: str) -> float:
    lower = (unit or "").lower()
    if lower == "s":
        return value * 1000.0
    return value


def to_pct(value: float) -> float:
    if 0 <= value <= 1:
        return value * 100.0
    return value


def add_sleep_overlap(acc: dict[str, DailyAccumulator], start_dt: datetime, end_dt: datetime) -> None:
    cursor = start_dt
    while cursor < end_dt:
        next_midnight = (cursor + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        segment_end = min(end_dt, next_midnight)
        overlap_hours = (segment_end - cursor).total_seconds() / 3600.0
        if overlap_hours > 0:
            acc[cursor.date().isoformat()].add_sum("sleep_hours", overlap_hours)
        cursor = segment_end


def update_field(acc: DailyAccumulator, field_name: str, value: float) -> None:
    if field_name in {"steps", "exercise_minutes", "active_energy_kcal", "sleep_hours"}:
        acc.add_sum(field_name, value)
    elif field_name in {"resting_hr", "hrv_ms", "blood_glucose_mmol_l", "blood_oxygen_pct", "heart_rate_avg"}:
        acc.add_avg(field_name, value)
    elif field_name == "weight_kg":
        acc.set_last(field_name, value)
    elif field_name == "heart_rate_min":
        acc.add_min(field_name, value)
    elif field_name == "heart_rate_max":
        acc.add_max(field_name, value)


def load_xml_history(path: Path) -> tuple[list[dict[str, float | str]], str | None]:
    daily: dict[str, DailyAccumulator] = defaultdict(DailyAccumulator)
    latest_date: str | None = None

    context = ET.iterparse(path, events=("end",))
    for _event, elem in context:
        if elem.tag != "Record":
            continue

        record_type = elem.attrib.get("type", "")
        start_dt = parse_dt(elem.attrib.get("startDate"))
        end_dt = parse_dt(elem.attrib.get("endDate"))
        value = to_float(elem.attrib.get("value"))
        unit = elem.attrib.get("unit", "")

        if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
            if elem.attrib.get("value") in SLEEP_ASLEEP_VALUES and start_dt and end_dt:
                add_sleep_overlap(daily, start_dt, end_dt)
                date_str = end_dt.date().isoformat()
                latest_date = max(latest_date, date_str) if latest_date else date_str
            elem.clear()
            continue

        field_name = XML_RECORD_TO_FIELD.get(record_type)
        if not field_name or start_dt is None or value is None:
            elem.clear()
            continue

        date_str = start_dt.date().isoformat()
        acc = daily[date_str]

        if field_name == "active_energy_kcal":
            update_field(acc, field_name, to_kcal(value, unit))
        elif field_name == "hrv_ms":
            update_field(acc, field_name, to_ms(value, unit))
        elif field_name == "blood_oxygen_pct":
            update_field(acc, field_name, to_pct(value))
        elif field_name == "weight_kg":
            if (unit or "").lower() in {"lb", "lbs", "pound", "pounds"}:
                update_field(acc, field_name, value * 0.45359237)
            else:
                update_field(acc, field_name, value)
        elif field_name == "heart_rate_avg":
            update_field(acc, "heart_rate_avg", value)
            update_field(acc, "heart_rate_min", value)
            update_field(acc, "heart_rate_max", value)
        else:
            update_field(acc, field_name, value)

        latest_date = max(latest_date, date_str) if latest_date else date_str
        elem.clear()

    rows = [daily[d].as_row(d) for d in sorted(daily.keys())]
    return rows, latest_date


def extract_json_metric_objects(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("metrics"), list):
            return payload["metrics"]
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("metrics"), list):
            return data["metrics"]
    return []


def load_recent_json_history(path: Path, after_date: str | None) -> list[dict[str, float | str]]:
    merged_by_date: dict[str, dict[str, float | str]] = {}
    cutoff = date.fromisoformat(after_date) if after_date else None

    for json_path in sorted(path.glob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        metrics = extract_json_metric_objects(payload)
        file_daily: dict[str, DailyAccumulator] = defaultdict(DailyAccumulator)
        for metric in metrics:
            name = normalize_name(str(metric.get("metric") or metric.get("name") or ""))
            field_name = JSON_METRIC_TO_FIELD.get(name)
            unit = str(metric.get("unit") or metric.get("units") or "")
            if not field_name:
                continue
            for entry in metric.get("data", []):
                start_dt = parse_dt(entry.get("startDate") or entry.get("date") or entry.get("sleepStart"))
                end_dt = parse_dt(entry.get("endDate") or entry.get("sleepEnd"))
                if field_name == "sleep_hours":
                    value = to_float(entry.get("total") if entry.get("total") is not None else entry.get("qty"))
                    if value is None and start_dt and end_dt:
                        value = (end_dt - start_dt).total_seconds() / 3600.0
                    if value is None:
                        continue
                    if start_dt and end_dt:
                        if cutoff and end_dt.date() <= cutoff:
                            continue
                        add_sleep_overlap(file_daily, start_dt, end_dt)
                    elif start_dt:
                        if cutoff and start_dt.date() <= cutoff:
                            continue
                        update_field(file_daily[start_dt.date().isoformat()], "sleep_hours", to_hours(value, unit))
                    continue

                dt = start_dt or end_dt
                if dt is None:
                    continue
                if cutoff and dt.date() <= cutoff:
                    continue
                value = to_float(
                    entry.get("qty")
                    if entry.get("qty") is not None
                    else entry.get("value")
                    if entry.get("value") is not None
                    else entry.get("total")
                )
                if value is None:
                    continue
                acc = file_daily[dt.date().isoformat()]
                if field_name == "active_energy_kcal":
                    update_field(acc, field_name, to_kcal(value, unit))
                elif field_name == "hrv_ms":
                    update_field(acc, field_name, to_ms(value, unit))
                elif field_name == "blood_oxygen_pct":
                    update_field(acc, field_name, to_pct(value))
                elif field_name == "weight_kg":
                    update_field(acc, field_name, value)
                elif field_name == "heart_rate_avg":
                    update_field(acc, "heart_rate_avg", value)
                    update_field(acc, "heart_rate_min", value)
                    update_field(acc, "heart_rate_max", value)
                else:
                    update_field(acc, field_name, value)

        for date_str in sorted(file_daily.keys()):
            merged_by_date[date_str] = file_daily[date_str].as_row(date_str)

    return [merged_by_date[d] for d in sorted(merged_by_date.keys())]


def merge_rows(xml_rows: list[dict[str, float | str]], json_rows: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    merged: dict[str, dict[str, float | str]] = {str(row["date"]): dict(row) for row in xml_rows}
    for row in json_rows:
        merged[str(row["date"])] = dict(row)
    return [merged[d] for d in sorted(merged.keys())]


def to_series(rows: list[dict[str, float | str]], field_name: str) -> tuple[list[date], list[float]]:
    dates: list[date] = []
    values: list[float] = []
    for row in rows:
        value = row.get(field_name)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            dates.append(date.fromisoformat(str(row["date"])))
            values.append(float(value))
    return dates, values


def latest_value(rows: list[dict[str, float | str]], field_name: str) -> tuple[str | None, float | None]:
    dates, values = to_series(rows, field_name)
    if not values:
        return None, None
    return dates[-1].isoformat(), values[-1]


def window_mean(rows: list[dict[str, float | str]], field_name: str, days: int, end_date: date | None) -> float | None:
    if end_date is None:
        return None
    start_date = end_date - timedelta(days=days - 1)
    values = [
        float(row[field_name])
        for row in rows
        if isinstance(row.get(field_name), (int, float))
        and start_date <= date.fromisoformat(str(row["date"])) <= end_date
    ]
    if not values:
        return None
    return float(sum(values) / len(values))


def rolling_average(values: list[float], window: int) -> np.ndarray:
    arr = np.array(values, dtype=float)
    if len(arr) < window:
        return arr.copy()
    result = np.empty_like(arr)
    for idx in range(len(arr)):
        start = max(0, idx - window + 1)
        result[idx] = arr[start : idx + 1].mean()
    return result


def fmt_value(field_name: str, value: float | None) -> str:
    if value is None:
        return "n/a"
    meta = METRIC_META.get(field_name, {"decimals": 1, "unit": ""})
    decimals = int(meta["decimals"])
    unit = str(meta["unit"])
    if decimals == 0:
        formatted = f"{value:,.0f}"
    else:
        formatted = f"{value:,.{decimals}f}".rstrip("0").rstrip(".")
    return f"{formatted}{(' ' + unit) if unit else ''}"


def delta_label(field_name: str, latest: float | None, baseline: float | None) -> tuple[str, str]:
    if latest is None or baseline is None:
        return "insufficient data", "neutral"
    delta = latest - baseline
    meta = METRIC_META[field_name]
    decimals = int(meta["decimals"])
    if abs(delta) < (0.05 if decimals else 0.5):
        return "near baseline", "neutral"
    direction = "up" if delta > 0 else "down"
    status = "good" if (direction == "up") == (meta["good_direction"] == "up") else "watch"
    sign = "+" if delta > 0 else ""
    if decimals == 0:
        delta_text = f"{sign}{delta:.0f}"
    else:
        delta_text = f"{sign}{delta:.1f}"
    unit = meta["unit"]
    unit_suffix = f" {unit}" if unit else ""
    return f"{delta_text}{unit_suffix} vs 30d", status


def status_sentence(rows: list[dict[str, float | str]]) -> dict[str, Any]:
    latest_date_str = str(rows[-1]["date"]) if rows else None
    latest_dt = date.fromisoformat(latest_date_str) if latest_date_str else None

    cards: list[dict[str, str]] = []
    for field_name in ("sleep_hours", "steps", "exercise_minutes", "resting_hr", "hrv_ms", "blood_oxygen_pct", "weight_kg"):
        _, latest = latest_value(rows, field_name)
        trailing_30 = window_mean(rows, field_name, 30, latest_dt)
        if latest is None and trailing_30 is None:
            continue
        delta_text, tone = delta_label(field_name, latest, trailing_30)
        cards.append(
            {
                "field": field_name,
                "label": METRIC_META[field_name]["label"],
                "latest": fmt_value(field_name, latest),
                "trailing_30": fmt_value(field_name, trailing_30),
                "delta": delta_text,
                "tone": tone,
            }
        )

    sentences: list[str] = []
    latest_sleep = latest_value(rows, "sleep_hours")[1]
    sleep_30 = window_mean(rows, "sleep_hours", 30, latest_dt)
    if latest_sleep is not None and sleep_30 is not None:
        if latest_sleep < 6:
            sentences.append(
                f"Sleep is the clearest current constraint: the latest recorded night was {fmt_value('sleep_hours', latest_sleep)}, below your recent {fmt_value('sleep_hours', sleep_30)} baseline."
            )
        elif latest_sleep >= 7:
            sentences.append(
                f"Recent sleep looks decent by your own baseline: the latest recorded night was {fmt_value('sleep_hours', latest_sleep)}."
            )

    latest_steps = latest_value(rows, "steps")[1]
    steps_30 = window_mean(rows, "steps", 30, latest_dt)
    if latest_steps is not None and steps_30 is not None:
        if latest_steps < 0.75 * steps_30:
            sentences.append(
                f"Activity dipped on the latest day: {fmt_value('steps', latest_steps)} versus a {fmt_value('steps', steps_30)} 30-day average."
            )
        elif latest_steps > 1.15 * steps_30:
            sentences.append(
                f"Activity was above baseline on the latest day: {fmt_value('steps', latest_steps)} versus a {fmt_value('steps', steps_30)} 30-day average."
            )

    latest_rhr = latest_value(rows, "resting_hr")[1]
    rhr_30 = window_mean(rows, "resting_hr", 30, latest_dt)
    latest_hrv = latest_value(rows, "hrv_ms")[1]
    hrv_30 = window_mean(rows, "hrv_ms", 30, latest_dt)
    if latest_rhr is not None and rhr_30 is not None and latest_hrv is not None and hrv_30 is not None:
        if latest_rhr <= rhr_30 and latest_hrv >= hrv_30:
            sentences.append("Recovery markers look better than your recent baseline: resting heart rate is not elevated and HRV is not suppressed.")
        elif latest_rhr > rhr_30 and latest_hrv < hrv_30:
            sentences.append("Recovery markers look somewhat stressed versus baseline: resting heart rate is up while HRV is down.")

    spo2_latest = latest_value(rows, "blood_oxygen_pct")[1]
    if spo2_latest is not None:
        if spo2_latest >= 95:
            sentences.append(f"Blood oxygen on the latest recorded day was {fmt_value('blood_oxygen_pct', spo2_latest)}, which looks reassuring in isolation.")
        else:
            sentences.append(f"Latest blood oxygen was {fmt_value('blood_oxygen_pct', spo2_latest)}; worth tracking for consistency, especially given the sleep-apnea history.")

    return {"cards": cards, "sentences": sentences, "latest_date": latest_date_str}


def apply_chart_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#f6f3ee",
            "axes.facecolor": "#fffdf8",
            "axes.edgecolor": "#d6d0c4",
            "axes.labelcolor": "#1f2937",
            "axes.titlecolor": "#111827",
            "xtick.color": "#4b5563",
            "ytick.color": "#4b5563",
            "grid.color": "#d7e0ea",
            "grid.alpha": 0.45,
            "font.size": 10.5,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_svg(fig: plt.Figure, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", bbox_inches="tight")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue().decode("utf-8")


def chart_timeseries(
    rows: list[dict[str, float | str]],
    fields: list[str],
    title: str,
    subtitle: str,
    output_name: str,
    bars_field: str | None = None,
) -> str:
    apply_chart_style()
    fig, axes = plt.subplots(len(fields), 1, figsize=(11.5, 2.9 * len(fields)), sharex=True)
    if len(fields) == 1:
        axes = [axes]

    for ax, field_name in zip(axes, fields):
        dates, values = to_series(rows, field_name)
        if not values:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(METRIC_META[field_name]["label"])
            continue
        color = CHART_COLORS.get(field_name, "#1d4ed8")
        if bars_field == field_name:
            ax.bar(dates, values, width=0.85, color=color, alpha=0.7)
        else:
            ax.plot(dates, values, color=color, linewidth=2.4)
            ax.scatter(dates[-10:], values[-10:], color=color, s=20, zorder=3)
        roll = rolling_average(values, 7)
        ax.plot(dates, roll, color="#111827", linewidth=1.7, linestyle=(0, (5, 3)), alpha=0.8)
        ax.set_title(METRIC_META[field_name]["label"], loc="left")
        ax.grid(True, axis="y")
        ax.set_ylabel(METRIC_META[field_name]["unit"])

    axes[0].text(0.0, 1.18, title, transform=axes[0].transAxes, fontsize=16, fontweight="bold", color="#0f172a")
    axes[0].text(0.0, 1.08, subtitle, transform=axes[0].transAxes, fontsize=10.5, color="#475569")
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    for label in axes[-1].get_xticklabels():
        label.set_rotation(0)
        label.set_ha("center")

    return save_svg(fig, ASSETS_DIR / output_name)


def chart_latest_vs_baseline(rows: list[dict[str, float | str]], fields: list[str], output_name: str) -> str:
    apply_chart_style()
    latest_date_str = str(rows[-1]["date"])
    latest_dt = date.fromisoformat(latest_date_str)
    labels: list[str] = []
    latest_values: list[float] = []
    baseline_values: list[float] = []
    colors: list[str] = []

    for field_name in fields:
        _, latest = latest_value(rows, field_name)
        baseline = window_mean(rows, field_name, 30, latest_dt)
        if latest is None or baseline is None:
            continue
        labels.append(METRIC_META[field_name]["label"])
        latest_values.append(latest)
        baseline_values.append(baseline)
        colors.append(CHART_COLORS.get(field_name, "#1d4ed8"))

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    if labels:
        x = np.arange(len(labels))
        ax.bar(x - 0.18, baseline_values, width=0.34, color="#cbd5e1", label="30-day avg")
        ax.bar(x + 0.18, latest_values, width=0.34, color=colors, label="Latest")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend(frameon=False, ncol=2, loc="upper right")
        ax.grid(True, axis="y")
    else:
        ax.text(0.5, 0.5, "No comparable data", ha="center", va="center", transform=ax.transAxes)
    ax.set_title("Latest day versus your 30-day baseline", loc="left")
    ax.text(0, 1.05, "Quick view of where the newest readings sit relative to recent normal.", transform=ax.transAxes, color="#475569")
    return save_svg(fig, ASSETS_DIR / output_name)


def metric_coverage(rows: list[dict[str, float | str]]) -> list[dict[str, Any]]:
    result = []
    for field_name in METRIC_META:
        dates, values = to_series(rows, field_name)
        if not values:
            continue
        result.append(
            {
                "field": field_name,
                "label": METRIC_META[field_name]["label"],
                "days": len(values),
                "first_date": dates[0].isoformat(),
                "last_date": dates[-1].isoformat(),
            }
        )
    return result


def build_html(summary: dict[str, Any], charts: dict[str, str], coverage: list[dict[str, Any]], rows: list[dict[str, float | str]]) -> str:
    cards_html = "\n".join(
        f"""
        <div class="metric-card tone-{card['tone']}">
          <div class="metric-label">{card['label']}</div>
          <div class="metric-latest">{card['latest']}</div>
          <div class="metric-baseline">30d avg: {card['trailing_30']}</div>
          <div class="metric-delta">{card['delta']}</div>
        </div>
        """
        for card in summary["cards"]
    )
    summary_html = "\n".join(f"<li>{sentence}</li>" for sentence in summary["sentences"])
    coverage_rows = "\n".join(
        f"<tr><td>{item['label']}</td><td>{item['days']}</td><td>{item['first_date']}</td><td>{item['last_date']}</td></tr>"
        for item in coverage
    )
    latest_date = summary.get("latest_date") or "n/a"
    first_date = str(rows[0]["date"]) if rows else "n/a"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Health Dashboard</title>
  <style>
    :root {{
      --bg: #efe9dd;
      --paper: #fffdf8;
      --ink: #0f172a;
      --muted: #475569;
      --line: #d7d0c4;
      --good: #e2f4eb;
      --watch: #fff0d9;
      --neutral: #edf2f7;
      --accent: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(29,78,216,0.10), transparent 28rem),
        radial-gradient(circle at top right, rgba(15,118,110,0.09), transparent 24rem),
        var(--bg);
      color: var(--ink);
      line-height: 1.45;
    }}
    .wrap {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 28px 20px 56px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,248,235,0.95));
      border: 1px solid rgba(214,208,196,0.95);
      border-radius: 28px;
      padding: 28px;
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 700;
    }}
    h1 {{
      margin: 8px 0 10px;
      font-size: clamp(32px, 4vw, 52px);
      line-height: 0.98;
    }}
    .subhead {{
      color: var(--muted);
      max-width: 72ch;
      font-size: 17px;
    }}
    .stats-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 20px;
    }}
    .stats-strip div {{
      background: rgba(255,255,255,0.75);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 16px;
    }}
    .stats-strip .value {{
      display: block;
      font-size: 24px;
      font-weight: 700;
      margin-top: 4px;
    }}
    .section {{
      margin-top: 24px;
      display: grid;
      gap: 18px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .metric-card {{
      border-radius: 20px;
      padding: 16px;
      border: 1px solid var(--line);
      background: var(--paper);
      box-shadow: 0 10px 24px rgba(15,23,42,0.05);
    }}
    .tone-good {{ background: linear-gradient(180deg, var(--good), var(--paper)); }}
    .tone-watch {{ background: linear-gradient(180deg, var(--watch), var(--paper)); }}
    .tone-neutral {{ background: linear-gradient(180deg, var(--neutral), var(--paper)); }}
    .metric-label {{ color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; }}
    .metric-latest {{ font-size: 30px; font-weight: 700; margin: 6px 0 4px; }}
    .metric-baseline, .metric-delta {{ color: var(--muted); font-size: 14px; }}
    .panel {{
      background: rgba(255,255,255,0.86);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 18px;
      box-shadow: 0 12px 28px rgba(15,23,42,0.06);
    }}
    .panel h2 {{
      margin: 0 0 10px;
      font-size: 22px;
    }}
    .summary-list {{
      margin: 0;
      padding-left: 18px;
    }}
    .summary-list li {{
      margin: 10px 0;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 18px;
    }}
    .chart {{
      overflow: hidden;
    }}
    .chart svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid #ece6db;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    .footnote {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 10px;
    }}
    @media (max-width: 720px) {{
      .wrap {{ padding: 16px 12px 36px; }}
      .hero {{ padding: 20px; border-radius: 22px; }}
      .panel {{ padding: 14px; border-radius: 18px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Apple Health Status</div>
      <h1>Current health, grounded in your own baseline</h1>
      <p class="subhead">This dashboard combines the historical Apple Health export with the newer daily sync files. It is a trend report, not medical advice. The goal is to show what looks stable, what looks constrained right now, and where the dataset is still thin.</p>
      <div class="stats-strip">
        <div><span>History window</span><span class="value">{first_date}</span></div>
        <div><span>Latest synced day</span><span class="value">{latest_date}</span></div>
        <div><span>Total daily rows</span><span class="value">{len(rows)}</span></div>
      </div>
    </section>

    <section class="section">
      <div class="cards">{cards_html}</div>
      <div class="panel">
        <h2>Plain-English read</h2>
        <ul class="summary-list">{summary_html}</ul>
      </div>
    </section>

    <section class="section chart-grid">
      <div class="panel chart">{charts['sleep_recovery']}</div>
      <div class="panel chart">{charts['activity']}</div>
      <div class="panel chart">{charts['baseline_compare']}</div>
    </section>

    <section class="section">
      <div class="panel">
        <h2>Metric coverage</h2>
        <table>
          <thead>
            <tr><th>Metric</th><th>Days</th><th>First day</th><th>Latest day</th></tr>
          </thead>
          <tbody>
            {coverage_rows}
          </tbody>
        </table>
        <p class="footnote">Coverage varies by sensor and by when you started wearing the Apple Watch or recording a metric. Weight, blood glucose, and blood oxygen are more sparse than sleep and steps.</p>
      </div>
    </section>
  </div>
</body>
</html>
"""


def write_summary_json(summary: dict[str, Any], coverage: list[dict[str, Any]], rows: list[dict[str, float | str]]) -> None:
    latest_row = rows[-1] if rows else {}
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "latest_date": summary.get("latest_date"),
        "total_rows": len(rows),
        "cards": summary["cards"],
        "sentences": summary["sentences"],
        "coverage": coverage,
        "latest_row": latest_row,
    }
    OUTPUT_SUMMARY.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a current-health dashboard from Apple Health data.")
    parser.add_argument("--export-xml", default=str(EXPORT_XML), help="Path to Apple Health export.xml")
    parser.add_argument("--raw-json-dir", default=str(RAW_JSON_DIR), help="Directory of recent daily Health Auto Export JSON files")
    parser.add_argument("--output-html", default=str(OUTPUT_HTML), help="Output HTML dashboard path")
    args = parser.parse_args()

    export_xml = Path(args.export_xml).expanduser()
    raw_json_dir = Path(args.raw_json_dir).expanduser()
    output_html = Path(args.output_html).expanduser()

    if not export_xml.exists():
        raise SystemExit(f"export.xml not found: {export_xml}")

    TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    xml_rows, xml_latest_date = load_xml_history(export_xml)
    json_rows = load_recent_json_history(raw_json_dir, xml_latest_date)
    rows = merge_rows(xml_rows, json_rows)
    if not rows:
        raise SystemExit("No health rows found.")

    summary = status_sentence(rows)
    coverage = metric_coverage(rows)

    charts = {
        "sleep_recovery": chart_timeseries(
            rows,
            ["sleep_hours", "resting_hr", "hrv_ms", "blood_oxygen_pct"],
            "Sleep and recovery",
            "Raw daily values with a 7-day rolling average overlay.",
            "sleep_recovery.svg",
        ),
        "activity": chart_timeseries(
            rows,
            ["steps", "exercise_minutes", "active_energy_kcal"],
            "Movement and load",
            "Steps show daily volume; exercise and active energy show intentional effort and output.",
            "activity_load.svg",
            bars_field="steps",
        ),
        "baseline_compare": chart_latest_vs_baseline(
            rows,
            ["sleep_hours", "steps", "exercise_minutes", "resting_hr", "hrv_ms", "blood_oxygen_pct"],
            "latest_vs_baseline.svg",
        ),
    }

    html = build_html(summary, charts, coverage, rows)
    output_html.write_text(html, encoding="utf-8")
    write_summary_json(summary, coverage, rows)

    latest_date_str = summary.get("latest_date") or "n/a"
    print(f"Built health dashboard with {len(rows)} daily rows")
    print(f"Latest date: {latest_date_str}")
    print(f"HTML: {output_html}")
    print(f"Summary JSON: {OUTPUT_SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
