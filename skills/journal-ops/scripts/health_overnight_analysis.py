#!/usr/bin/env python3
"""
Overnight health analysis helpers for morning workflow and daily interview prep.

Focuses on metrics where daily averages hide important overnight variation,
especially blood oxygen around sleep / CPAP use.
"""

from __future__ import annotations

import json
import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from health_paths import apple_health_export_xml, health_auto_export_raw_dir, resolve_health_records_root
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
DEFAULT_EXPORT_XML = apple_health_export_xml(ROOT)
DEFAULT_RAW_JSON_DIR = health_auto_export_raw_dir(ROOT)
OVERNIGHT_CACHE_DIR = resolve_health_records_root(ROOT) / ".cache" / "overnight_analysis"

SLEEP_ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
}

LOCAL_TZ = datetime.now().astimezone().tzinfo


@dataclass
class SleepInterval:
    start: datetime
    end: datetime


@dataclass
class TimedSample:
    timestamp: datetime
    value: float


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.astimezone(LOCAL_TZ) if LOCAL_TZ is not None else parsed
        except ValueError:
            continue
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None and LOCAL_TZ is not None:
            return parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ) if parsed.tzinfo is not None and LOCAL_TZ is not None else parsed
    except ValueError:
        return None


def normalize_name(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("_", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace("/", " ")
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


def oxygen_to_pct(value: float) -> float:
    if 0 <= value <= 1:
        return value * 100.0
    return value


def extract_json_metric_objects(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("metrics"), list):
            return payload["metrics"]
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("metrics"), list):
            return data["metrics"]
    return []


def overnight_window(target_date: str) -> tuple[datetime, datetime]:
    d = date.fromisoformat(target_date)
    end = datetime.combine(d, datetime.min.time()).astimezone() + timedelta(hours=12)
    start = end - timedelta(hours=18)
    return start, end


def overlaps(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> bool:
    return start < window_end and end > window_start


def latest_json_candidates(raw_json_dir: Path) -> list[Path]:
    return sorted(raw_json_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def _source_state(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"path": "", "mtime_ns": None, "size": None}
    stat = path.stat()
    return {"path": str(path), "mtime_ns": stat.st_mtime_ns, "size": stat.st_size}


def _cache_path_for(target_date: str) -> Path:
    return OVERNIGHT_CACHE_DIR / f"{target_date}.json"


def _truthy_env(name: str) -> bool | None:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return None
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def should_allow_xml_fallback(target_date: str) -> bool:
    override = _truthy_env("LIFEREPO_HEALTH_ALLOW_XML_FALLBACK")
    if override is not None:
        return override
    # Morning runs usually target "today", and current-day JSON exports often do
    # not yet include overnight sleep/SpO2. Avoid reparsing the full XML export
    # on that path unless explicitly requested.
    return target_date != date.today().isoformat()


def load_cached_result(target_date: str, *, export_xml: Path, latest_json: Path | None) -> dict[str, Any] | None:
    cache_path = _cache_path_for(target_date)
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    expected_state = {
        "target_date": target_date,
        "export_xml": _source_state(export_xml),
        "latest_json": _source_state(latest_json),
    }
    if payload.get("cache_state") != expected_state:
        return None

    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    result = dict(result)
    result["source"] = "xml-cache"
    return result


def save_cached_result(target_date: str, *, export_xml: Path, latest_json: Path | None, result: dict[str, Any]) -> None:
    cache_path = _cache_path_for(target_date)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cache_state": {
            "target_date": target_date,
            "export_xml": _source_state(export_xml),
            "latest_json": _source_state(latest_json),
        },
        "result": result,
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def collect_from_json(raw_json_dir: Path, target_date: str) -> tuple[list[SleepInterval], list[TimedSample], list[TimedSample]]:
    window_start, window_end = overnight_window(target_date)
    sleep_intervals: list[SleepInterval] = []
    oxygen_samples: list[TimedSample] = []
    hr_samples: list[TimedSample] = []

    for json_path in latest_json_candidates(raw_json_dir):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        metrics = extract_json_metric_objects(payload)
        if not metrics:
            continue

        file_sleep: list[SleepInterval] = []
        file_oxygen: list[TimedSample] = []
        file_hr: list[TimedSample] = []

        for metric in metrics:
            metric_name = normalize_name(str(metric.get("metric") or metric.get("name") or ""))
            data = metric.get("data", [])
            if metric_name == "sleep analysis":
                for entry in data:
                    start = parse_dt(entry.get("sleepStart") or entry.get("startDate") or entry.get("date"))
                    end = parse_dt(entry.get("sleepEnd") or entry.get("endDate"))
                    total = to_float(entry.get("total"))
                    if start and end and overlaps(start, end, window_start, window_end):
                        file_sleep.append(SleepInterval(start=start, end=end))
                    elif start and total is not None:
                        end = start + timedelta(hours=total)
                        if overlaps(start, end, window_start, window_end):
                            file_sleep.append(SleepInterval(start=start, end=end))
            elif metric_name in {"blood oxygen saturation", "oxygen saturation"}:
                for entry in data:
                    ts = parse_dt(entry.get("date") or entry.get("startDate"))
                    value = to_float(entry.get("qty") if entry.get("qty") is not None else entry.get("value"))
                    if ts and value is not None and window_start <= ts <= window_end:
                        file_oxygen.append(TimedSample(timestamp=ts, value=oxygen_to_pct(value)))
            elif metric_name == "heart rate":
                for entry in data:
                    ts = parse_dt(entry.get("date") or entry.get("startDate"))
                    value = to_float(entry.get("qty") if entry.get("qty") is not None else entry.get("value"))
                    if ts and value is not None and window_start <= ts <= window_end:
                        file_hr.append(TimedSample(timestamp=ts, value=value))

        if file_sleep or file_oxygen or file_hr:
            return (
                sorted(file_sleep, key=lambda x: x.start),
                sorted(file_oxygen, key=lambda x: x.timestamp),
                sorted(file_hr, key=lambda x: x.timestamp),
            )

    return sleep_intervals, oxygen_samples, hr_samples


def collect_from_xml(export_xml: Path, target_date: str) -> tuple[list[SleepInterval], list[TimedSample], list[TimedSample]]:
    window_start, window_end = overnight_window(target_date)
    sleep_intervals: list[SleepInterval] = []
    oxygen_samples: list[TimedSample] = []
    hr_samples: list[TimedSample] = []

    context = ET.iterparse(export_xml, events=("end",))
    for _event, elem in context:
        if elem.tag != "Record":
            continue
        record_type = elem.attrib.get("type", "")
        start = parse_dt(elem.attrib.get("startDate"))
        end = parse_dt(elem.attrib.get("endDate"))
        value = to_float(elem.attrib.get("value"))

        if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
            if elem.attrib.get("value") in SLEEP_ASLEEP_VALUES and start and end and overlaps(start, end, window_start, window_end):
                sleep_intervals.append(SleepInterval(start=start, end=end))
        elif record_type == "HKQuantityTypeIdentifierOxygenSaturation":
            if start and value is not None and window_start <= start <= window_end:
                oxygen_samples.append(TimedSample(timestamp=start, value=oxygen_to_pct(value)))
        elif record_type == "HKQuantityTypeIdentifierHeartRate":
            if start and value is not None and window_start <= start <= window_end:
                hr_samples.append(TimedSample(timestamp=start, value=value))

        elem.clear()

    return sleep_intervals, oxygen_samples, hr_samples


def overlap_sleep_only(samples: list[TimedSample], sleep_intervals: list[SleepInterval]) -> list[TimedSample]:
    if not sleep_intervals:
        return samples
    result = []
    for sample in samples:
        if any(interval.start <= sample.timestamp <= interval.end for interval in sleep_intervals):
            result.append(sample)
    return result


def total_sleep_hours(intervals: list[SleepInterval], target_date: str) -> float | None:
    if not intervals:
        return None
    window_start, window_end = overnight_window(target_date)
    total_seconds = 0.0
    for interval in intervals:
        start = max(interval.start, window_start)
        end = min(interval.end, window_end)
        if end > start:
            total_seconds += (end - start).total_seconds()
    return total_seconds / 3600.0 if total_seconds > 0 else None


def sample_stats(samples: list[TimedSample]) -> dict[str, Any]:
    if not samples:
        return {"count": 0}
    values = [sample.value for sample in samples if math.isfinite(sample.value)]
    if not values:
        return {"count": 0}
    values_sorted = sorted(values)
    count = len(values_sorted)
    median = values_sorted[count // 2] if count % 2 == 1 else (values_sorted[count // 2 - 1] + values_sorted[count // 2]) / 2.0
    below_94 = sum(1 for value in values_sorted if value < 94)
    below_92 = sum(1 for value in values_sorted if value < 92)
    below_90 = sum(1 for value in values_sorted if value < 90)
    lowest_sample = min(samples, key=lambda sample: sample.value)
    return {
        "count": count,
        "avg": sum(values_sorted) / count,
        "median": median,
        "min": values_sorted[0],
        "max": values_sorted[-1],
        "below_94_count": below_94,
        "below_92_count": below_92,
        "below_90_count": below_90,
        "below_94_pct": below_94 / count * 100.0,
        "below_92_pct": below_92 / count * 100.0,
        "below_90_pct": below_90 / count * 100.0,
        "lowest_timestamp": lowest_sample.timestamp.isoformat(),
    }


def classify_overnight_oxygen(stats: dict[str, Any]) -> tuple[str, list[str]]:
    if stats.get("count", 0) == 0:
        return "unknown", ["No overnight blood oxygen samples were found."]

    findings: list[str] = []
    severity = "ok"
    min_spo2 = stats["min"]
    below_90_pct = stats["below_90_pct"]
    below_92_pct = stats["below_92_pct"]

    if min_spo2 < 88 or below_90_pct >= 10:
        severity = "alert"
        findings.append(
            f"Overnight SpO2 dipped to {min_spo2:.1f}% with {below_90_pct:.0f}% of readings below 90%."
        )
    elif min_spo2 < 90 or below_92_pct >= 15:
        severity = "watch"
        findings.append(
            f"Overnight SpO2 showed some dips: nadir {min_spo2:.1f}%, {below_92_pct:.0f}% of readings below 92%."
        )
    else:
        findings.append(f"Overnight SpO2 looked stable: nadir {min_spo2:.1f}%, median {stats['median']:.1f}%.")

    return severity, findings


def analyze_overnight(target_date: str, export_xml: Path | None = None, raw_json_dir: Path | None = None) -> dict[str, Any]:
    export_xml = export_xml or DEFAULT_EXPORT_XML
    raw_json_dir = raw_json_dir or DEFAULT_RAW_JSON_DIR

    sleep_intervals, oxygen_samples, hr_samples = collect_from_json(raw_json_dir, target_date)
    source = "json"
    if not sleep_intervals and not oxygen_samples and export_xml.exists():
        latest_json = latest_json_candidates(raw_json_dir)
        latest_json_path = latest_json[0] if latest_json else None
        cached = load_cached_result(target_date, export_xml=export_xml, latest_json=latest_json_path)
        if cached is not None:
            return cached
        if should_allow_xml_fallback(target_date):
            sleep_intervals, oxygen_samples, hr_samples = collect_from_xml(export_xml, target_date)
            source = "xml"

    oxygen_during_sleep = overlap_sleep_only(oxygen_samples, sleep_intervals) or oxygen_samples
    hr_during_sleep = overlap_sleep_only(hr_samples, sleep_intervals) or hr_samples
    oxygen_stats = sample_stats(oxygen_during_sleep)
    hr_stats = sample_stats(hr_during_sleep)
    severity, findings = classify_overnight_oxygen(oxygen_stats)

    result = {
        "target_date": target_date,
        "source": source,
        "sleep_interval_count": len(sleep_intervals),
        "sleep_hours_window": total_sleep_hours(sleep_intervals, target_date),
        "oxygen_stats": oxygen_stats,
        "heart_rate_stats": hr_stats,
        "severity": severity,
        "findings": findings,
    }
    if source == "xml":
        latest_json = latest_json_candidates(raw_json_dir)
        latest_json_path = latest_json[0] if latest_json else None
        save_cached_result(target_date, export_xml=export_xml, latest_json=latest_json_path, result=result)
    return result


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"


def fmt_num(value: float | None, decimals: int = 1, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}{suffix}"
