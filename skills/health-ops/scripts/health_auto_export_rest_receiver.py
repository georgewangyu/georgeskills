#!/usr/bin/env python3
"""
Receive Health Auto Export REST API JSON payloads and normalize them into the
canonical daily health metrics CSV used by the journal workflow.

This supports two modes:

1. Server mode:
   python3 scripts/journal/health_auto_export_rest_receiver.py --serve

2. File ingestion mode:
   python3 scripts/journal/health_auto_export_rest_receiver.py --input-json payload.json

The receiver is intentionally tolerant of payload shape differences. It looks
for metric objects recursively, archives raw payloads, and upserts the canonical
CSV with the daily rows it can confidently derive.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import secrets
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from health_paths import daily_health_metrics_csv, health_auto_export_raw_dir
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
HEALTH_OPS_DIR = Path(__file__).resolve().parent
DEFAULT_DEST = daily_health_metrics_csv(ROOT)
DEFAULT_RAW_DIR = health_auto_export_raw_dir(ROOT)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
SYNC_SCRIPT = HEALTH_OPS_DIR / "sync_health_shortcut_metrics.py"

CANONICAL_FIELDS = [
    "date",
    "sleep_hours",
    "steps",
    "exercise_minutes",
    "active_energy_kcal",
    "resting_hr",
    "hrv_ms",
    "blood_glucose_mmol_l",
    "blood_oxygen_pct",
    "weight_kg",
    "heart_rate_avg",
    "heart_rate_min",
    "heart_rate_max",
]

SUM_METRICS = {"steps", "exercise_minutes", "active_energy_kcal", "sleep_hours"}
AVG_METRICS = {
    "resting_hr",
    "hrv_ms",
    "blood_glucose_mmol_l",
    "blood_oxygen_pct",
    "heart_rate_avg",
}
LAST_METRICS = {"weight_kg"}
MIN_METRICS = {"heart_rate_min"}
MAX_METRICS = {"heart_rate_max"}


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

    def to_row(self, date_str: str) -> dict[str, str]:
        row = {field: "" for field in CANONICAL_FIELDS}
        row["date"] = date_str
        for field_name, value in self.sums.items():
            row[field_name] = fmt_number(value)
        for field_name in AVG_METRICS:
            count = self.avg_counts.get(field_name, 0)
            if count:
                row[field_name] = fmt_number(self.avg_sums[field_name] / count)
        for field_name, value in self.mins.items():
            row[field_name] = fmt_number(value)
        for field_name, value in self.maxs.items():
            row[field_name] = fmt_number(value)
        for field_name, value in self.lasts.items():
            row[field_name] = fmt_number(value)
        return row


def fmt_number(value: float) -> str:
    if math.isfinite(value) and float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip().replace(",", "")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 1e12:
            return datetime.fromtimestamp(number / 1000.0, tz=timezone.utc)
        if number > 1e9:
            return datetime.fromtimestamp(number, tz=timezone.utc)
        # Apple reference date: 2001-01-01 UTC
        return datetime.fromtimestamp(978307200 + number, tz=timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            # Health Auto Export commonly emits timestamps like
            # "2026-04-17 08:04:46 -0700", which Python 3.9 does not accept via
            # fromisoformat because of the space-separated offset.
            for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S %z"):
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue
            return None
    return None


def normalize_metric_name(metric_name: str) -> str:
    normalized = metric_name.strip().lower()
    normalized = normalized.replace("%", " pct ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace("_", " ")
    normalized = " ".join(normalized.split())
    return normalized


def metric_to_field(metric_name: str) -> str | None:
    normalized = normalize_metric_name(metric_name)
    mapping = {
        "sleep analysis": "sleep_hours",
        "step count": "steps",
        "apple exercise time": "exercise_minutes",
        "active energy": "active_energy_kcal",
        "resting heart rate": "resting_hr",
        "heart rate variability": "hrv_ms",
        "blood glucose": "blood_glucose_mmol_l",
        "blood oxygen saturation": "blood_oxygen_pct",
        "oxygen saturation": "blood_oxygen_pct",
        "weight body mass": "weight_kg",
        "body mass": "weight_kg",
        "heart rate": "heart_rate_avg",
    }
    return mapping.get(normalized)


def alias_metric_name(metric_obj: dict[str, Any]) -> str:
    return str(metric_obj.get("metric") or metric_obj.get("name") or "").strip()


def convert_value(field_name: str, qty: float, unit: str) -> float:
    normalized_unit = unit.strip().lower()
    if field_name == "active_energy_kcal":
        if "kj" in normalized_unit:
            return qty / 4.184
        return qty
    if field_name == "blood_oxygen_pct":
        if 0 <= qty <= 1:
            return qty * 100.0
        return qty
    if field_name == "sleep_hours":
        if "sec" in normalized_unit:
            return qty / 3600.0
        if "min" in normalized_unit:
            return qty / 60.0
        return qty
    return qty


def date_from_entry(entry: dict[str, Any], fallback_date: datetime | None) -> str | None:
    for key in (
        "startDate",
        "start_date",
        "sleepStart",
        "inBedStart",
        "date",
        "timestamp",
        "time",
    ):
        dt = parse_timestamp(entry.get(key))
        if dt is not None:
            return dt.date().isoformat()
    if fallback_date is not None:
        return fallback_date.date().isoformat()
    return None


def sleep_date_from_entry(entry: dict[str, Any], fallback_date: datetime | None) -> str | None:
    for key in ("sleepEnd", "endDate", "end_date", "date"):
        dt = parse_timestamp(entry.get(key))
        if dt is not None:
            return dt.date().isoformat()
    return date_from_entry(entry, fallback_date)


def iter_metric_objects(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if any(k in node for k in ("metric", "name")) and any(
                k in node for k in ("data", "qty", "value", "values")
            ):
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def sleep_hours_from_entry(entry: dict[str, Any], unit: str) -> float | None:
    for key in ("totalSleep", "total", "qty", "value"):
        value = parse_float(entry.get(key))
        if value is not None:
            return convert_value("sleep_hours", value, unit)

    start = parse_timestamp(entry.get("startDate") or entry.get("start_date"))
    end = parse_timestamp(entry.get("endDate") or entry.get("end_date"))
    if start and end and end >= start:
        category = str(entry.get("category") or entry.get("label") or entry.get("phase") or "").lower()
        if category and not any(token in category for token in ("asleep", "inbed", "core", "deep", "rem")):
            return None
        return (end - start).total_seconds() / 3600.0

    return None


def extract_qty(entry: dict[str, Any]) -> float | None:
    for key in ("qty", "value", "avg", "average", "Avg", "sum", "total"):
        value = parse_float(entry.get(key))
        if value is not None:
            return value
    return None


def apply_metric_object(
    metric_obj: dict[str, Any],
    acc_map: dict[str, DailyAccumulator],
) -> None:
    metric_name = alias_metric_name(metric_obj)
    field_name = metric_to_field(metric_name)
    if not field_name:
        return

    unit = str(metric_obj.get("unit") or metric_obj.get("units") or "")
    fallback_dt = parse_timestamp(metric_obj.get("date"))
    data = metric_obj.get("data")

    # Some payloads may collapse directly to a value instead of an array.
    if isinstance(data, (int, float, str)):
        data = [{"qty": data}]
    elif isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        data = []

    if field_name == "sleep_hours":
        for entry in data:
            if not isinstance(entry, dict):
                continue
            date_str = sleep_date_from_entry(entry, fallback_dt)
            if not date_str:
                continue
            hours = sleep_hours_from_entry(entry, unit)
            if hours is None:
                continue
            acc_map[date_str].add_sum("sleep_hours", hours)
        return

    for entry in data:
        if not isinstance(entry, dict):
            continue
        date_str = date_from_entry(entry, fallback_dt)
        if not date_str:
            continue

        qty = extract_qty(entry)
        if qty is None:
            continue
        qty = convert_value(field_name, qty, unit)

        acc = acc_map[date_str]
        if field_name in SUM_METRICS:
            acc.add_sum(field_name, qty)
        elif field_name in AVG_METRICS:
            acc.add_avg(field_name, qty)
        elif field_name in LAST_METRICS:
            acc.set_last(field_name, qty)

        if field_name == "heart_rate_avg":
            min_qty = parse_float(entry.get("Min"))
            max_qty = parse_float(entry.get("Max"))
            acc.add_min("heart_rate_min", min_qty if min_qty is not None else qty)
            acc.add_max("heart_rate_max", max_qty if max_qty is not None else qty)


def payload_to_rows(payload: Any) -> list[dict[str, str]]:
    acc_map: dict[str, DailyAccumulator] = defaultdict(DailyAccumulator)
    metric_objects = iter_metric_objects(payload)
    if isinstance(payload, dict):
        inner = payload.get("data")
        if isinstance(inner, dict) and isinstance(inner.get("metrics"), list):
            metric_objects = [m for m in inner.get("metrics", []) if isinstance(m, dict)]
    for metric_obj in metric_objects:
        apply_metric_object(metric_obj, acc_map)
    return [acc_map[date_str].to_row(date_str) for date_str in sorted(acc_map.keys())]


def archive_payload(raw_dir: Path, payload: Any, session_id: str | None) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_part = (session_id or secrets.token_hex(4)).replace("/", "_")
    dest = raw_dir / f"{stamp}_{session_part}.json"
    with dest.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return dest


def load_existing_rows(dest_csv: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    if not dest_csv.exists():
        return list(CANONICAL_FIELDS), {}

    with dest_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        existing_fields = list(reader.fieldnames or [])
        fieldnames = list(existing_fields)
        for field_name in CANONICAL_FIELDS:
            if field_name not in fieldnames:
                fieldnames.append(field_name)

        rows = {}
        for row in reader:
            date = (row.get("date") or "").strip()
            if date:
                rows[date] = row
        return fieldnames, rows


def upsert_rows(dest_csv: Path, rows: list[dict[str, str]]) -> list[str]:
    fieldnames, existing = load_existing_rows(dest_csv)
    updated_dates: list[str] = []

    for row in rows:
        date = row["date"]
        if date not in existing:
            existing[date] = {field: "" for field in fieldnames}
            existing[date]["date"] = date

        target = existing[date]
        for field_name, value in row.items():
            if field_name == "date" or not value:
                continue
            target[field_name] = value
        updated_dates.append(date)

    dest_csv.parent.mkdir(parents=True, exist_ok=True)
    with dest_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for date in sorted(existing.keys()):
            writer.writerow(existing[date])

    return sorted(set(updated_dates))


def sync_daily_metrics(dest_csv: Path, write: bool) -> int:
    cmd = [
        "python3",
        str(SYNC_SCRIPT),
        "--health-csv",
        str(dest_csv),
    ]
    if write:
        cmd.append("--write")
    return subprocess.call(cmd)


def ingest_payload(
    payload: Any,
    dest_csv: Path,
    raw_dir: Path,
    session_id: str | None = None,
    sync_write: bool = False,
) -> dict[str, Any]:
    archived_path = archive_payload(raw_dir=raw_dir, payload=payload, session_id=session_id)
    rows = payload_to_rows(payload)
    updated_dates: list[str] = []
    if rows:
        updated_dates = upsert_rows(dest_csv=dest_csv, rows=rows)
    return {
        "archived_path": str(archived_path),
        "rows_found": len(rows),
        "updated_dates": updated_dates,
        "sync_exit_code": None,
    }


class ReceiverHandler(BaseHTTPRequestHandler):
    server_version = "HealthAutoExportReceiver/0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/api/healthautoexport/v1/daily-metrics/ingest", "/api/health"):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        token = getattr(self.server, "auth_token", "")
        if token:
            auth_header = self.headers.get("Authorization", "")
            if auth_header != f"Bearer {token}":
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "detail": str(exc)})
            return

        result = ingest_payload(
            payload=payload,
            dest_csv=getattr(self.server, "dest_csv"),
            raw_dir=getattr(self.server, "raw_dir"),
            session_id=self.headers.get("session-id"),
            sync_write=getattr(self.server, "sync_write"),
        )
        self._send_json(HTTPStatus.OK, {"ok": True, **result})

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console output concise and machine-readable.
        print(f"[receiver] {self.address_string()} - {format % args}")


def serve(host: str, port: int, dest_csv: Path, raw_dir: Path, auth_token: str, sync_write: bool) -> int:
    httpd = ThreadingHTTPServer((host, port), ReceiverHandler)
    httpd.dest_csv = dest_csv
    httpd.raw_dir = raw_dir
    httpd.auth_token = auth_token
    httpd.sync_write = sync_write
    print(f"Listening on http://{host}:{port}/api/healthautoexport/v1/daily-metrics/ingest")
    if auth_token:
        print("Authorization: Bearer <configured token>")
    print(f"Canonical CSV: {dest_csv}")
    print(f"Raw archive dir: {raw_dir}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Receive Health Auto Export REST API payloads")
    parser.add_argument("--serve", action="store_true", help="Run as a local HTTP server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server bind port")
    parser.add_argument("--auth-token", default=os.environ.get("HEALTH_AUTO_EXPORT_TOKEN", ""), help="Optional bearer token")
    parser.add_argument("--input-json", default="", help="Ingest a JSON payload from a file instead of serving HTTP")
    parser.add_argument("--dest-csv", default=str(DEFAULT_DEST), help="Canonical health CSV path")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR), help="Directory to archive raw payloads")
    parser.add_argument("--write", action="store_true", help="When ingesting, sync into journal/daily_metrics.csv")
    args = parser.parse_args()

    dest_csv = Path(args.dest_csv).expanduser()
    raw_dir = Path(args.raw_dir).expanduser()

    if args.input_json:
        payload_path = Path(args.input_json).expanduser()
        with payload_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        result = ingest_payload(
            payload=payload,
            dest_csv=dest_csv,
            raw_dir=raw_dir,
            session_id=payload_path.stem,
            sync_write=args.write,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.serve:
        return serve(
            host=args.host,
            port=args.port,
            dest_csv=dest_csv,
            raw_dir=raw_dir,
            auth_token=args.auth_token,
            sync_write=args.write,
        )

    parser.error("Choose either --serve or --input-json")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
