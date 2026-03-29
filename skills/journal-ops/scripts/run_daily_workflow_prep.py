#!/usr/bin/env python3
"""
Prepare daily workflow context with one command.

This wrapper runs the existing export/import scripts, chooses the best
available health source automatically, and prints a compact readiness
report for the target date.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from health_paths import apple_health_export_xml, daily_health_metrics_csv, resolve_health_source_records_root
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


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str


def run_step(name: str, cmd: list[str], *, ok_codes: set[int] | None = None) -> StepResult:
    ok_codes = ok_codes or {0}
    print(f"\n== {name} ==")
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    if proc.returncode in ok_codes:
        return StepResult(name=name, ok=True, detail=f"exit {proc.returncode}")
    return StepResult(name=name, ok=False, detail=f"exit {proc.returncode}")


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare daily workflow context with one command")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--skip-exports", action="store_true", help="Skip Apple Notes / email / calendar exports")
    parser.add_argument("--skip-health", action="store_true", help="Skip health import attempts")
    parser.add_argument(
        "--skip-memory",
        action="store_true",
        help="Skip structured-memory candidate refresh when a summary file exists",
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
        results.append(run_step("Apple Notes export", ["python3", str(APPLE_NOTES_EXPORT)]))
        results.append(run_step("Email export", ["python3", str(EMAIL_EXPORT)]))
        results.append(run_step("Calendar export", ["python3", str(CALENDAR_EXPORT)]))
    results.append(run_step("Email interview context", ["python3", str(PRINT_EMAIL), "--date", args.date]))
    results.append(run_step("Location interview context", ["python3", str(PRINT_LOCATION), "--date", args.date]))

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
                label = f"Health step {idx}"
                results.append(run_step(label, cmd))
            results.append(run_step("Health interview context", ["python3", str(PRINT_HEALTH), "--date", args.date]))

    results.append(run_step("Workflow completeness", ["python3", str(CHECK_COMPLETENESS), "--date", args.date], ok_codes={0, 1}))

    summary_path = summary_path_for(args.date)
    if not args.skip_memory:
        if summary_path.exists():
            results.append(
                run_step(
                    "Memory candidate refresh",
                    ["python3", str(MEMORY_EXTRACT), "--date", args.date],
                )
            )
        else:
            print("\n== Memory candidate refresh ==")
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
