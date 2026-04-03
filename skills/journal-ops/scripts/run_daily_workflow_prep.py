#!/usr/bin/env python3
"""
Prepare daily workflow context with one command.

This wrapper runs the existing export/import scripts, chooses the best
available health source automatically, and prints a compact readiness
report for the target date.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from health_paths import apple_health_export_xml, daily_health_metrics_csv, resolve_health_source_records_root
from health_overnight_analysis import analyze_overnight, fmt_pct
from print_location_interview_context import (
    PLACES_FILE,
    build_config as build_traccar_config,
    fetch_positions as fetch_traccar_positions,
    fetch_report_stops as fetch_traccar_report_stops,
    haversine_km,
    load_places as load_location_places,
    summarize_report_stops as summarize_location_report_stops,
    summarize_stop_clusters as summarize_location_stop_clusters,
)
from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
JOURNAL_OPS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts" / "journal"

APPLE_NOTES_EXPORT = ROOT / "scripts" / "exports" / "apple-notes" / "export_apple_notes.py"
EMAIL_EXPORT = ROOT / "scripts" / "exports" / "email" / "export_emails_gmail_api.py"
CALENDAR_EXPORT = ROOT / "scripts" / "exports" / "calendar" / "export_calendar_google.py"
IMPORT_HEALTH_AUTO = SCRIPTS_DIR / "import_health_auto_export_csv.py"
IMPORT_HEALTH_JSON = SCRIPTS_DIR / "import_health_auto_export_google_drive.py"
IMPORT_HEALTH_SHORTCUT = SCRIPTS_DIR / "import_health_shortcut_csv.py"
IMPORT_HEALTH_XML = SCRIPTS_DIR / "import_apple_health_export_xml.py"
PRINT_HEALTH = JOURNAL_OPS_DIR / "print_health_interview_context.py"
PRINT_EMAIL = JOURNAL_OPS_DIR / "print_email_interview_context.py"
PRINT_LOCATION = JOURNAL_OPS_DIR / "print_location_interview_context.py"
CHECK_COMPLETENESS = SCRIPTS_DIR / "check_daily_workflow_completeness.py"
MEMORY_EXTRACT = ROOT / "scripts" / "memory" / "extract_daily_summary_candidates.py"
AGENT_MANAGED_REFRESH = ROOT / "scripts" / "knowledge" / "refresh_agent_managed.py"
NOTES_LAST_EXPORT_MARKER = ROOT / "notes-private" / "apple-notes" / "all-notes" / ".last_export"
EMAIL_DIR = ROOT / "notes-private" / "email"
CALENDAR_DIR = ROOT / "notes-private" / "calendar"
CALENDAR_LOG = CALENDAR_DIR / "export.log"
CALENDAR_WEEKLY = CALENDAR_DIR / "weekly_calendar.md"
PREP_MARKERS_DIR = ROOT / "journal" / ".workflow_prep_markers"
DEFAULT_EXPORT_FRESHNESS_SECONDS = 300

HEALTH_AUTO_EXPORTS_ROOT = resolve_health_source_records_root(ROOT)
ICLOUD_HEALTH_EXPORT_ROOT = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~com~ifunography~HealthExport"
    / "Documents"
    / "iCloud drive"
)
SHORTCUT_HEALTH_SOURCE = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Shortcuts"
    / "daily_health_metrics.csv"
)
APPLE_HEALTH_XML = apple_health_export_xml(ROOT)
CANONICAL_HEALTH_CSV = daily_health_metrics_csv(ROOT)
SECTION_ORDER = [
    "Today at a Glance",
    "Daily Metrics",
    "Health Context",
    "Location Context",
    "Sprints Today",
    "Deep Sprint Plan",
    "Light Block Plan",
    "Highlights",
    "Challenges",
    "Key Decisions",
    "People / Relationships",
    "Tomorrow Priorities",
    "Purchases / Spending",
    "Notes Highlights",
    "Important Emails",
    "Conversation Milestones",
    "Narrator Notes",
    "Reflections",
]
LEVEL2_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", flags=re.MULTILINE)


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ParallelStepSpec:
    name: str
    cmd: list[str]
    ok_codes: set[int] | None = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_dt(dt: datetime) -> str:
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_age(seconds: float) -> str:
    total = max(int(seconds), 0)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _mtime_utc(path: Path) -> datetime | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _max_dt(*values: datetime | None) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _prep_marker_path(name: str) -> Path:
    return PREP_MARKERS_DIR / f"{name}.json"


def read_prep_marker(name: str) -> tuple[str | None, datetime | None]:
    path = _prep_marker_path(name)
    if not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, None

    target_date = str(payload.get("target_date", "")).strip() or None
    raw_completed_at = str(payload.get("completed_at", "")).strip()
    if not raw_completed_at:
        return target_date, None
    try:
        completed_at = datetime.fromisoformat(raw_completed_at)
    except ValueError:
        return target_date, None
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    return target_date, completed_at.astimezone(timezone.utc)


def write_prep_marker(name: str, *, target_date: str) -> None:
    PREP_MARKERS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "target_date": target_date,
        "completed_at": _now_utc().isoformat(),
    }
    _prep_marker_path(name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def latest_apple_notes_activity() -> datetime | None:
    _, prep_time = read_prep_marker("apple_notes")
    return _max_dt(prep_time, _mtime_utc(NOTES_LAST_EXPORT_MARKER))


def latest_email_activity() -> datetime | None:
    _, prep_time = read_prep_marker("email")
    email_markers = sorted(EMAIL_DIR.glob(".last_incremental_export_*"))
    email_time = None
    if email_markers:
        email_time = max(_mtime_utc(marker) for marker in email_markers)
    return _max_dt(prep_time, email_time)


def latest_calendar_success() -> datetime | None:
    _, prep_time = read_prep_marker("calendar")
    success_time = None
    if CALENDAR_LOG.exists():
        text = CALENDAR_LOG.read_text(encoding="utf-8", errors="ignore")
        lines = [line for line in text.splitlines() if "Calendar export completed successfully" in line]
        if lines:
            match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", lines[-1])
            if match:
                parsed = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
                success_time = parsed.astimezone(timezone.utc)
    return _max_dt(prep_time, success_time, _mtime_utc(CALENDAR_WEEKLY))


def maybe_skip_fresh_export(
    *,
    name: str,
    freshness_key: str,
    target_date: str,
    freshness_seconds: int,
    force_exports: bool,
) -> StepResult | None:
    if force_exports or freshness_seconds <= 0:
        return None

    target_date_seen, prep_time = read_prep_marker(freshness_key)
    latest_activity = None
    activity_source = ""

    if prep_time is not None and target_date_seen == target_date:
        latest_activity = prep_time
        activity_source = "prep marker"
    elif target_date == date.today().isoformat():
        if freshness_key == "apple_notes":
            latest_activity = latest_apple_notes_activity()
        elif freshness_key == "email":
            latest_activity = latest_email_activity()
        elif freshness_key == "calendar":
            latest_activity = latest_calendar_success()
        activity_source = "export output"

    if latest_activity is None:
        return None

    age_seconds = (_now_utc() - latest_activity).total_seconds()
    if age_seconds > freshness_seconds:
        return None

    detail = (
        "skipped (fresh export via "
        f"{activity_source}; last success {_format_age(age_seconds)} ago at {_format_dt(latest_activity)})"
    )
    print(f"\n== {name} ==")
    print(detail)
    return StepResult(name=name, ok=True, detail=detail)


def _print_proc_output(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)


def run_step(name: str, cmd: list[str], *, ok_codes: set[int] | None = None) -> StepResult:
    ok_codes = ok_codes or {0}
    print(f"\n== {name} ==")
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    if proc.returncode in ok_codes:
        return StepResult(name=name, ok=True, detail=f"exit {proc.returncode}")
    return StepResult(name=name, ok=False, detail=f"exit {proc.returncode}")


def run_step_captured(name: str, cmd: list[str], *, ok_codes: set[int] | None = None) -> StepResult:
    ok_codes = ok_codes or {0}
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    print(f"\n== {name} ==")
    print("$", " ".join(cmd))
    _print_proc_output(proc)
    if proc.returncode in ok_codes:
        return StepResult(name=name, ok=True, detail=f"exit {proc.returncode}")
    return StepResult(name=name, ok=False, detail=f"exit {proc.returncode}")


def run_steps_parallel(step_specs: list[ParallelStepSpec]) -> list[StepResult]:
    if not step_specs:
        return []

    results_by_index: dict[int, StepResult] = {}
    with ThreadPoolExecutor(max_workers=len(step_specs)) as executor:
        futures = [
            executor.submit(run_step_captured, spec.name, spec.cmd, ok_codes=spec.ok_codes)
            for spec in step_specs
        ]
        for idx, future in enumerate(futures):
            results_by_index[idx] = future.result()

    return [results_by_index[idx] for idx in range(len(step_specs))]


def latest_health_auto_export_csv() -> Path | None:
    candidates = sorted(
        HEALTH_AUTO_EXPORTS_ROOT.glob("HealthAutoExport_*/HealthAutoExport-*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def latest_health_auto_export_json() -> Path | None:
    if not ICLOUD_HEALTH_EXPORT_ROOT.exists():
        return None
    candidates = sorted(
        ICLOUD_HEALTH_EXPORT_ROOT.rglob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def health_auto_export_json_for_date(day_text: str) -> Path | None:
    if not ICLOUD_HEALTH_EXPORT_ROOT.exists():
        return None
    candidates = sorted(
        ICLOUD_HEALTH_EXPORT_ROOT.rglob(f"HealthAutoExport-{day_text}.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def choose_health_source(target_date: str) -> tuple[str, list[list[str]]] | None:
    auto_json = health_auto_export_json_for_date(target_date)
    if auto_json:
        return (
            f"Health Auto Export JSON (date-matched): {auto_json}",
            [["python3", str(IMPORT_HEALTH_JSON), "--input-json", str(auto_json), "--write"]],
        )

    auto_json = latest_health_auto_export_json()
    if auto_json:
        return (
            f"Health Auto Export JSON (latest fallback): {auto_json}",
            [["python3", str(IMPORT_HEALTH_JSON), "--input-json", str(auto_json), "--write"]],
        )

    auto_csv = latest_health_auto_export_csv()
    if auto_csv:
        return (
            f"Health Auto Export CSV: {auto_csv}",
            [["python3", str(IMPORT_HEALTH_AUTO)]],
        )

    if SHORTCUT_HEALTH_SOURCE.exists():
        return (
            f"Shortcut CSV: {SHORTCUT_HEALTH_SOURCE}",
            [["python3", str(IMPORT_HEALTH_SHORTCUT), "--write"]],
        )

    if APPLE_HEALTH_XML.exists():
        return (
            f"Apple Health export.xml: {APPLE_HEALTH_XML}",
            [["python3", str(IMPORT_HEALTH_XML)]],
        )

    return None


def summary_path_for(day_text: str) -> Path:
    year, month, _ = day_text.split("-")
    return ROOT / "journal" / "summaries" / year / month / f"{day_text}_Summary.md"


def note_count_for(day_text: str) -> int:
    notes_dir = ROOT / "notes-private" / "apple-notes" / "all-notes"
    return len(list(notes_dir.glob(f"{day_text}_*")))


def email_count_for(day_text: str) -> int:
    email_dir = ROOT / "notes-private" / "email"
    return len(list(email_dir.glob(f"**/{day_text}_*")))


def reflection_exists_for(day_text: str) -> bool:
    return (ROOT / "journal" / "reflections" / f"{day_text}_Thoughts.md").exists()


def _parse_float(value: str | None) -> float | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _fmt_num(value: float | None, *, decimals: int = 1, suffix: str = "") -> str:
    if value is None:
        return "missing"
    return f"{value:.{decimals}f}{suffix}"


def _fmt_steps(value: float | None) -> str:
    if value is None:
        return "missing"
    if value >= 1000:
        return f"~{value / 1000:.1f}k"
    return f"{value:.0f}"


def _load_health_row(day_text: str) -> dict[str, str] | None:
    if not CANONICAL_HEALTH_CSV.exists():
        return None
    with CANONICAL_HEALTH_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("date") or "").strip() == day_text:
                return row
    return None


def build_health_section(day_text: str) -> str | None:
    row = _load_health_row(day_text)
    if row is None:
        return None

    sleep_hours = _parse_float(row.get("sleep_hours"))
    resting_hr = _parse_float(row.get("resting_hr"))
    exercise_minutes = _parse_float(row.get("exercise_minutes"))
    steps = _parse_float(row.get("steps"))
    active_energy = _parse_float(row.get("active_energy_kcal"))
    hrv = _parse_float(row.get("hrv_ms"))
    avg_hr = _parse_float(row.get("heart_rate_avg"))
    min_hr = _parse_float(row.get("heart_rate_min"))
    max_hr = _parse_float(row.get("heart_rate_max"))
    blood_oxygen = _parse_float(row.get("blood_oxygen_pct"))

    lines = [
        "- Apple Health snapshot:"
        f" `{_fmt_num(sleep_hours, decimals=2, suffix='h')}` sleep,"
        f" `{_fmt_num(resting_hr, decimals=0, suffix=' bpm')}` resting HR,"
        f" `{_fmt_num(exercise_minutes, decimals=0, suffix=' min')}` exercise,"
        f" `{_fmt_steps(steps)}` steps,"
        f" `{_fmt_num(active_energy, decimals=1, suffix=' kcal')}` active energy.",
    ]

    cardio_parts: list[str] = []
    if hrv is not None:
        cardio_parts.append(f"HRV `{_fmt_num(hrv, decimals=2, suffix=' ms')}`")
    if avg_hr is not None:
        cardio_parts.append(f"average HR `{_fmt_num(avg_hr, decimals=2, suffix=' bpm')}`")
    if min_hr is not None or max_hr is not None:
        cardio_parts.append(
            "range"
            f" `{_fmt_num(min_hr, decimals=0)}-{_fmt_num(max_hr, decimals=0)} bpm`"
        )
    if cardio_parts:
        lines.append(f"- Cardiovascular context: {', '.join(cardio_parts)}.")

    overnight = analyze_overnight(day_text)
    oxygen_stats = overnight.get("oxygen_stats", {})
    oxygen_count = oxygen_stats.get("count", 0) or 0
    if blood_oxygen is not None or oxygen_count:
        oxygen_sentence = (
            "- Oxygen context"
            f" looked {overnight.get('severity', 'unknown')} overnight:"
            f" blood oxygen `{_fmt_num(blood_oxygen, decimals=2, suffix='%')}`"
        )
        if oxygen_count:
            oxygen_sentence += (
                ", overnight SpO2"
                f" min `{fmt_pct(oxygen_stats.get('min'))}`,"
                f" median `{fmt_pct(oxygen_stats.get('median'))}`,"
                f" average `{fmt_pct(oxygen_stats.get('avg'))}`"
            )
        oxygen_sentence += "."
        lines.append(oxygen_sentence)

    missing_fields: list[str] = []
    if _parse_float(row.get("blood_glucose_mmol_l")) is None:
        missing_fields.append("blood glucose")
    if _parse_float(row.get("weight_kg")) is None:
        missing_fields.append("weight")
    if missing_fields:
        lines.append(f"- Missing data for this date: {', '.join(missing_fields)}.")

    return "\n".join(lines)


def build_location_section(day_text: str) -> str | None:
    config = build_traccar_config()
    if config is None:
        return None
    try:
        positions = fetch_traccar_positions(config, day_text)
    except Exception:
        return None
    if not positions:
        return None

    total_distance_km = 0.0
    max_speed = 0.0
    for prev, cur in zip(positions, positions[1:]):
        total_distance_km += haversine_km(prev, cur)
        max_speed = max(max_speed, cur.speed_kph)

    places = load_location_places(PLACES_FILE)
    stops: list[str] = []
    try:
        stops = summarize_location_report_stops(fetch_traccar_report_stops(config, day_text), places)
    except Exception:
        stops = []
    if not stops:
        stops = summarize_location_stop_clusters(positions, places)

    first = positions[0]
    last = positions[-1]
    lines = [
        "- First seen at"
        f" `{first.timestamp.strftime('%H:%M')}` and last seen at"
        f" `{last.timestamp.strftime('%H:%M')}`, with about"
        f" `{total_distance_km:.1f} km` of total travel."
    ]
    if stops:
        stop_text = "; ".join(f"`{stop}`" for stop in stops[:5])
        lines.append(f"- Longer stops that defined the day: {stop_text}.")
    lines.append(f"- Peak observed speed was `{max_speed:.1f} km/h`.")
    return "\n".join(lines)


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"\A---\n.*?\n---\n", text, flags=re.DOTALL)
    if not match:
        return "", text
    return text[:match.end()], text[match.end():]


def extract_level2_headers(text: str) -> dict[str, tuple[int, int]]:
    matches = list(LEVEL2_HEADER_RE.finditer(text))
    sections: dict[str, tuple[int, int]] = {}
    for idx, match in enumerate(matches):
        title = re.sub(r"\s+\(Optional\)$", "", match.group(1).strip()).strip()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[title] = (match.start(), end)
    return sections


def upsert_level2_section(text: str, title: str, body: str) -> str:
    frontmatter, markdown_body = split_frontmatter(text)
    sections = extract_level2_headers(markdown_body)
    block = f"## {title}\n\n{body.strip()}\n"

    if title in sections:
        start, end = sections[title]
        updated_body = (
            markdown_body[:start].rstrip("\n")
            + "\n\n"
            + block
            + "\n"
            + markdown_body[end:].lstrip("\n")
        )
        return frontmatter + updated_body.lstrip("\n")

    insert_at = len(markdown_body)
    if title in SECTION_ORDER:
        current_idx = SECTION_ORDER.index(title)
        for later_title in SECTION_ORDER[current_idx + 1:]:
            if later_title in sections:
                insert_at = sections[later_title][0]
                break

    if insert_at == len(markdown_body):
        updated_body = markdown_body.rstrip("\n") + "\n\n" + block
    else:
        updated_body = (
            markdown_body[:insert_at].rstrip("\n")
            + "\n\n"
            + block
            + "\n"
            + markdown_body[insert_at:].lstrip("\n")
        )
    return frontmatter + updated_body.lstrip("\n")


def ensure_level2_section(text: str, title: str, body: str) -> str:
    _, markdown_body = split_frontmatter(text)
    if title in extract_level2_headers(markdown_body):
        return text
    return upsert_level2_section(text, title, body)


def hydrate_summary_context(day_text: str) -> StepResult:
    summary_path = summary_path_for(day_text)
    if not summary_path.exists():
        return StepResult("Summary context sync", True, "skipped (summary missing)")

    original = summary_path.read_text(encoding="utf-8")
    updated = original
    changed_sections: list[str] = []

    health_body = build_health_section(day_text)
    if health_body:
        updated = upsert_level2_section(updated, "Health Context", health_body)
        changed_sections.append("Health Context")

    location_body = build_location_section(day_text)
    if location_body:
        updated = upsert_level2_section(updated, "Location Context", location_body)
        changed_sections.append("Location Context")

    before = updated
    updated = ensure_level2_section(updated, "Conversation Milestones", "- Not logged yet.")
    if updated != before:
        changed_sections.append("Conversation Milestones")

    before = updated
    updated = ensure_level2_section(updated, "Narrator Notes", "- Not logged yet.")
    if updated != before:
        changed_sections.append("Narrator Notes")

    if updated == original:
        return StepResult("Summary context sync", True, "no changes")

    summary_path.write_text(updated, encoding="utf-8")
    return StepResult("Summary context sync", True, f"updated {', '.join(changed_sections)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare daily workflow context with one command")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--skip-exports", action="store_true", help="Skip Apple Notes / email / calendar exports")
    parser.add_argument(
        "--force-exports",
        action="store_true",
        help="Run notes/email/calendar exports even when the prep runner already refreshed them recently.",
    )
    parser.add_argument(
        "--export-freshness-seconds",
        type=int,
        default=DEFAULT_EXPORT_FRESHNESS_SECONDS,
        help="Same-day export reruns inside this freshness window are skipped unless --force-exports is set (default: 300).",
    )
    parser.add_argument("--skip-health", action="store_true", help="Skip health import attempts")
    parser.add_argument(
        "--skip-memory",
        action="store_true",
        help="Skip structured-memory candidate refresh when a summary file exists",
    )
    parser.add_argument(
        "--skip-doc-memory",
        action="store_true",
        help="When refreshing memory candidates, only use the daily summary source (skip other memory-eligible docs).",
    )
    parser.add_argument(
        "--skip-agent-managed",
        action="store_true",
        help="Skip compiled knowledge refresh for the agent-managed middle layer.",
    )
    parser.add_argument(
        "--allow-health-miss",
        action="store_true",
        help="Return success even when no health source is available",
    )
    args = parser.parse_args()

    results: list[StepResult] = []

    print(f"Target date: {args.date}")
    print(f"Summary path: {summary_path_for(args.date)}")

    if not args.skip_exports:
        export_specs = [
            ("Apple Notes export", ["python3", str(APPLE_NOTES_EXPORT)], "apple_notes"),
            ("Email export", ["python3", str(EMAIL_EXPORT)], "email"),
            ("Calendar export", ["python3", str(CALENDAR_EXPORT)], "calendar"),
        ]
        exports_to_run: list[ParallelStepSpec] = []
        export_keys_to_update: list[str] = []
        for name, cmd, freshness_key in export_specs:
            skipped = maybe_skip_fresh_export(
                name=name,
                freshness_key=freshness_key,
                target_date=args.date,
                freshness_seconds=args.export_freshness_seconds,
                force_exports=args.force_exports,
            )
            if skipped is not None:
                results.append(skipped)
                continue
            exports_to_run.append(ParallelStepSpec(name=name, cmd=cmd))
            export_keys_to_update.append(freshness_key)
        if exports_to_run:
            export_results = run_steps_parallel(exports_to_run)
            results.extend(export_results)
            for freshness_key, result in zip(export_keys_to_update, export_results):
                if result.ok:
                    write_prep_marker(freshness_key, target_date=args.date)

    initial_parallel_steps: list[ParallelStepSpec] = [
        ParallelStepSpec("Email interview context", ["python3", str(PRINT_EMAIL), "--date", args.date]),
        ParallelStepSpec("Location interview context", ["python3", str(PRINT_LOCATION), "--date", args.date]),
    ]

    health_missing = False
    if not args.skip_health:
        chosen = choose_health_source(args.date)
        if chosen is None:
            health_missing = True
            print("\n== Health import ==")
            print("No supported health source found.")
            print(f"- Missing Health Auto Export JSON under: {ICLOUD_HEALTH_EXPORT_ROOT}")
            print(f"- Missing Health Auto Export CSV under: {HEALTH_AUTO_EXPORTS_ROOT}")
            print(f"- Missing Shortcut CSV at: {SHORTCUT_HEALTH_SOURCE}")
            print(f"- Missing Apple Health XML at: {APPLE_HEALTH_XML}")
            results.append(StepResult("Health import", False, "no available source"))
        else:
            source_label, commands = chosen
            print("\n== Health import source ==")
            print(source_label)
            for idx, cmd in enumerate(commands, start=1):
                initial_parallel_steps.append(ParallelStepSpec(f"Health step {idx}", cmd))

    results.extend(run_steps_parallel(initial_parallel_steps))

    if not args.skip_health and not health_missing:
        results.append(run_step("Health interview context", ["python3", str(PRINT_HEALTH), "--date", args.date]))

    results.append(hydrate_summary_context(args.date))
    results.append(run_step("Workflow completeness", ["python3", str(CHECK_COMPLETENESS), "--date", args.date], ok_codes={0, 1}))

    summary_path = summary_path_for(args.date)
    if not args.skip_memory:
        if summary_path.exists():
            memory_cmd = ["python3", str(MEMORY_EXTRACT), "--date", args.date]
            if not args.skip_doc_memory:
                memory_cmd.append("--also-docs")
            results.append(
                run_step(
                    "Memory candidate refresh",
                    memory_cmd,
                )
            )
        else:
            print("\n== Memory candidate refresh ==")
            print("Skipped: summary file does not exist yet.")

    if not args.skip_agent_managed:
        if summary_path.exists() and AGENT_MANAGED_REFRESH.exists():
            results.append(
                run_step(
                    "Agent-managed knowledge refresh",
                    ["python3", str(AGENT_MANAGED_REFRESH), "--date", args.date, "--apply-safe"],
                )
            )
        elif not AGENT_MANAGED_REFRESH.exists():
            print("\n== Agent-managed knowledge refresh ==")
            print("Skipped: refresh script is not available yet.")
        else:
            print("\n== Agent-managed knowledge refresh ==")
            print("Skipped: summary file does not exist yet.")

    print("\n== Context snapshot ==")
    print(f"- Summary exists: {'yes' if summary_path.exists() else 'no'}")
    print(f"- Apple Notes for date: {note_count_for(args.date)}")
    print(f"- Emails for date: {email_count_for(args.date)}")
    print(f"- Reflection exists: {'yes' if reflection_exists_for(args.date) else 'no'}")

    failed = [r for r in results if not r.ok]
    print("\n== Result summary ==")
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"- {status}: {r.name} ({r.detail})")

    if failed and not (health_missing and args.allow_health_miss and len(failed) == 1):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
