#!/usr/bin/env python3
"""
Morning brief for start-of-day chat.

This is meant to be the script behind a cue like "morning" or
"this is the start of my day".
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from datetime import date
from pathlib import Path

from health_paths import daily_health_metrics_csv
from health_overnight_analysis import analyze_overnight, fmt_num
from repo_paths import resolve_private_repo_root


ROOT = resolve_private_repo_root()
JOURNAL_OPS_DIR = Path(__file__).resolve().parent
PRINT_HEALTH = JOURNAL_OPS_DIR / "print_health_interview_context.py"
CHECK_COMPLETENESS = ROOT / "scripts" / "journal" / "check_daily_workflow_completeness.py"
RUN_PREP = JOURNAL_OPS_DIR / "run_daily_workflow_prep.py"
HEALTH_CSV = daily_health_metrics_csv(ROOT)
GITHUB_TRENDS_SCRIPT = JOURNAL_OPS_DIR.parents[1] / "github-trends-ops" / "scripts" / "fetch_github_trends.py"



def summary_path_for(day_text: str) -> Path:
    year, month, _ = day_text.split("-")
    return ROOT / "journal" / "summaries" / year / month / f"{day_text}_Summary.md"


def summary_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("summary_status:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def workflow_started(day_text: str) -> bool:
    return summary_path_for(day_text).exists()


def health_metrics_present(day_text: str) -> bool:
    if not HEALTH_CSV.exists():
        return False
    with HEALTH_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return any((row.get("date") or "").strip() == day_text for row in reader)


def completeness_exit(day_text: str) -> int:
    proc = subprocess.run(
        ["python3", str(CHECK_COMPLETENESS), "--date", day_text],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return proc.returncode


def print_github_trends():
    if not GITHUB_TRENDS_SCRIPT.exists():
        return

    print("\n--- GitHub Trending ---")
    for period in ["daily", "weekly"]:
        proc = subprocess.run(
            ["python3", str(GITHUB_TRENDS_SCRIPT), "--since", period, "--limit", "3"],
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0:
            print(proc.stdout.strip())
        else:
            print(f"  (Error fetching {period} trends)")

    # Simple signal analysis based on trends
    # In a real scenario, this could be more sophisticated (e.g., matching keywords against user projects)
    print("\n- Planning note: Open-source activity is a key proxy for market attention. Look for overlaps with your current stack (ADA, BitePath) or emerging AI agent patterns.")


def print_morning_publishing_loop():
    print("\n--- Morning Publishing Prompt ---")
    print("- Pick one to three candidate ideas from current work, the latest summary, or the GitHub trends signal.")
    print("- Ask George which one he wants to post about.")
    print("- After he chooses, draft or refine one public-safe markdown note in liferepo/writing/shareable/.")
    print("- If the note is worth shipping, create the gist first and then convert it into a hook-first X thread via xbot.")
    print("- Keep the gist link in the final reply, not the opener.")
    print("- Log the gist URL and tweet IDs under Conversation Milestones in today's summary.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a morning brief for the current day.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--run-prep-if-missing",
        action="store_true",
        help="If the workflow has not been started for today, run daily workflow prep automatically.",
    )
    parser.add_argument(
        "--skip-exports-on-auto-prep",
        action="store_true",
        help="When auto-running prep, skip notes/email/calendar exports.",
    )
    args = parser.parse_args()

    day_text = args.date
    summary = summary_path_for(day_text)
    started = workflow_started(day_text)
    status = summary_status(summary)
    completeness = completeness_exit(day_text)
    has_health_row = health_metrics_present(day_text)
    overnight = analyze_overnight(day_text)

    if args.run_prep_if_missing and not started:
        cmd = ["python3", str(RUN_PREP), "--date", day_text]
        if args.skip_exports_on_auto_prep:
            cmd.append("--skip-exports")
        subprocess.run(cmd, cwd=ROOT, text=True)
        started = workflow_started(day_text)
        status = summary_status(summary)
        completeness = completeness_exit(day_text)
        has_health_row = health_metrics_present(day_text)

    print(f"Morning brief for {day_text}")
    print(f"- Daily workflow started: {'yes' if started else 'no'}")
    print(f"- Summary status: {status}")
    print(f"- Workflow completeness exit: {completeness} (0=complete, 1=incomplete)")
    print(f"- Health metrics row for today: {'yes' if has_health_row else 'no'}")

    oxygen = overnight["oxygen_stats"]
    print(f"- Overnight severity: {overnight['severity']}")
    for finding in overnight["findings"]:
        print(f"  - {finding}")
    if oxygen.get("count", 0):
        print(
            "- Overnight oxygen detail:"
            f" samples={oxygen['count']},"
            f" min={fmt_num(oxygen.get('min'), 1, '%')},"
            f" avg={fmt_num(oxygen.get('avg'), 1, '%')},"
            f" below90={fmt_num(oxygen.get('below_90_pct'), 0, '%')},"
            f" below92={fmt_num(oxygen.get('below_92_pct'), 0, '%')},"
            f" below94={fmt_num(oxygen.get('below_94_pct'), 0, '%')}"
        )

    sleep_hours = overnight.get("sleep_hours_window")
    if sleep_hours is not None:
        if sleep_hours < 6:
            print(f"- Planning note: treat today as a recovery-leaning day unless your subjective energy feels clearly better than the sleep data suggests ({sleep_hours:.2f} h in overnight window).")
        elif sleep_hours < 7:
            print(f"- Planning note: moderate day. Protect the morning for one hard thing, but avoid overloading the schedule ({sleep_hours:.2f} h in overnight window).")
        else:
            print(f"- Planning note: sleep duration looks solid enough to support a normal hard-morning plan ({sleep_hours:.2f} h in overnight window).")
    else:
        print("- Planning note: no overnight sleep window was derived, so use subjective energy more heavily today.")

    print("\nSuggested next command:")
    print(f"python3 {PRINT_HEALTH} --date {day_text}")

    print_github_trends()
    print_morning_publishing_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
