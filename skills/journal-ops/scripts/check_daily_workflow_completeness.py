#!/usr/bin/env python3
"""
Check daily workflow completeness for summaries, metrics, and export freshness.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
SUMMARIES_DIR = ROOT / "journal" / "summaries"
METRICS_CSV = ROOT / "journal" / "daily_metrics.csv"
EMAIL_DIR = ROOT / "captures" / "email"
CALENDAR_LOG = ROOT / "captures" / "calendar" / "export.log"


@dataclass
class DayCheck:
    day: date
    summary_state: str
    summary_status_header: str
    metrics_row: bool
    notes: str


STABLE_HEADERS = {
    "Today at a Glance",
    "Daily Metrics",
    "Health Context",
    "Location Context",
    "Sprints Today",
    "Highlights",
    "Challenges",
    "Key Decisions",
    "People / Relationships",
    "Tomorrow Priorities",
}

PLANNED_REQUIRED_HEADERS = {
    "Today at a Glance",
    "Deep Sprint Plan",
}

ACTIVE_MEMORY_HEADERS = {
    "Key Decisions",
    "People / Relationships",
    "Tomorrow Priorities",
    "Conversation Milestones",
    "Narrator Notes",
}


def iter_days(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def summary_path(day: date) -> Path:
    return SUMMARIES_DIR / day.strftime("%Y") / day.strftime("%m") / f"{day.isoformat()}_Summary.md"


def parse_summary_status_header(text: str) -> str:
    if not text.startswith("---"):
        return "missing"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "missing"
    header = parts[1]
    for line in header.splitlines():
        line = line.strip()
        if line.startswith("summary_status:"):
            return line.split(":", 1)[1].strip() or "missing"
    return "missing"


def detect_summary_state(text: str) -> str:
    has_metrics_section = "## Daily Metrics" in text
    has_sprints_section = "## Sprints Today" in text
    has_glance_section = "## Today at a Glance" in text
    has_plan_section = "## Deep Sprint Plan" in text

    metric_rows = re.findall(r"^\|\s*(Energy|Mood|Focus|Productivity).*?\|\s*(.*?)\s*\|$", text, flags=re.MULTILINE)
    placeholder_values = {"", "not logged yet", "unknown", "n/a", "na", "-", "tbd"}
    non_blank_metrics = any(val.strip().lower() not in placeholder_values for _, val in metric_rows)

    if has_plan_section and not has_metrics_section and not has_sprints_section:
        return "planned_only"

    if has_metrics_section and has_sprints_section and has_glance_section and non_blank_metrics:
        return "completed_candidate"

    if has_plan_section and has_metrics_section and not non_blank_metrics:
        return "partial"

    return "partial"


def extract_level2_headers(text: str) -> set[str]:
    headers: set[str] = set()
    for match in re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE):
        title = match.group(1).strip()
        title = re.sub(r"\s+\(Optional\)$", "", title).strip()
        headers.add(title)
    return headers


def load_metrics_dates() -> set[str]:
    if not METRICS_CSV.exists():
        return set()
    rows = set()
    with METRICS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            day = (row.get("Date") or "").strip()
            if day:
                rows.add(day)
    return rows


def check_date(day: date, metrics_dates: set[str]) -> DayCheck:
    path = summary_path(day)
    if not path.exists():
        return DayCheck(day, "missing_file", "missing", day.isoformat() in metrics_dates, "create summary")

    text = path.read_text(encoding="utf-8")
    status = parse_summary_status_header(text)
    state = detect_summary_state(text)
    has_metrics_row = day.isoformat() in metrics_dates

    note_parts: list[str] = []
    if status == "missing":
        note_parts.append("add summary_status header")
    elif status not in {"planned", "partial", "completed"}:
        note_parts.append("unknown header value")

    headers = extract_level2_headers(text)
    if status == "planned":
        missing = sorted(PLANNED_REQUIRED_HEADERS - headers)
        if missing:
            note_parts.append(f"missing planned headers: {', '.join(missing)}")
    else:
        missing = sorted(STABLE_HEADERS - headers)
        if missing:
            note_parts.append(f"missing stable headers: {', '.join(missing)}")

    # Memory-sensitive section names should stay stable once the day is active.
    if status in {"partial", "completed"}:
        for header in sorted(ACTIVE_MEMORY_HEADERS):
            if header not in headers:
                note_parts.append(f"missing memory header: {header}")

    notes = "; ".join(note_parts)
    return DayCheck(day, state, status, has_metrics_row, notes)


def parse_export_freshness() -> tuple[str, str]:
    email_markers = sorted(EMAIL_DIR.glob(".last_incremental_export_*"))
    marker_text = "missing"
    if email_markers:
        latest = max(m.stat().st_mtime for m in email_markers)
        marker_text = datetime.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M:%S")

    cal_text = "missing"
    if CALENDAR_LOG.exists():
        text = CALENDAR_LOG.read_text(encoding="utf-8", errors="ignore")
        lines = [ln for ln in text.splitlines() if "Calendar export completed successfully" in ln]
        if lines:
            match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", lines[-1])
            cal_text = match.group(1) if match else lines[-1]
    return marker_text, cal_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Check daily workflow completeness.")
    parser.add_argument("--date", help="Single date YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=7, help="Lookback window ending today")
    args = parser.parse_args()

    if args.date:
        end_day = datetime.strptime(args.date, "%Y-%m-%d").date()
        start_day = end_day
    else:
        end_day = date.today()
        start_day = end_day - timedelta(days=max(args.days - 1, 0))

    metrics_dates = load_metrics_dates()
    results = [check_date(d, metrics_dates) for d in iter_days(start_day, end_day)]

    print("date        summary_state       status_header  metrics_row  notes")
    print("-" * 78)
    failed = 0
    for r in results:
        metric_flag = "yes" if r.metrics_row else "no"
        print(f"{r.day.isoformat()}  {r.summary_state:17}  {r.summary_status_header:12}  {metric_flag:10}  {r.notes}")
        if r.summary_state in {"missing_file", "planned_only", "partial"} or not r.metrics_row or r.notes:
            failed += 1

    email_fresh, cal_fresh = parse_export_freshness()
    print("\nexport_freshness:")
    print(f"  email_markers_last_modified: {email_fresh}")
    print(f"  calendar_last_success_line:  {cal_fresh}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
