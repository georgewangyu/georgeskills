#!/usr/bin/env python3
"""
Run a lightweight unattended memory-maintenance pass.

This does not call an LLM. It refreshes recent candidates, validates memory
files, and writes a compact review report that highlights what likely needs
human promotion, reinforcement, or cleanup.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
MEMORY_DIR = PRIVATE_REPO_ROOT / "memory"
CANDIDATES_DIR = MEMORY_DIR / "candidates"
REPORTS_DIR = MEMORY_DIR / "reports"
SCRIPT_DIR = Path(__file__).resolve().parent
EXTRACT_SCRIPT = SCRIPT_DIR / "extract_daily_summary_candidates.py"
VALIDATE_SCRIPT = SCRIPT_DIR / "validate_memory_records.py"

CANONICAL_FILES = {
    "decision": MEMORY_DIR / "decisions.jsonl",
    "commitment": MEMORY_DIR / "commitments.jsonl",
    "status_change": MEMORY_DIR / "status_changes.jsonl",
    "person": MEMORY_DIR / "people.jsonl",
    "pattern": MEMORY_DIR / "patterns.jsonl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lightweight memory maintenance pass.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Anchor date in YYYY-MM-DD.")
    parser.add_argument("--refresh-days", type=int, default=3, help="Refresh candidate extraction for this many recent dates.")
    parser.add_argument("--lookback-days", type=int, default=14, help="Look back this many days for pending candidate analysis.")
    parser.add_argument("--skip-docs", action="store_true", help="Refresh recent candidates from summaries only.")
    parser.add_argument("--report-path", help="Optional explicit report path.")
    return parser.parse_args()


def iter_dates(anchor: str, days: int) -> list[str]:
    base = datetime.strptime(anchor, "%Y-%m-%d").date()
    return [(base - timedelta(days=offset)).isoformat() for offset in range(days)]


def summary_path_for(day_text: str) -> Path:
    year, month, _ = day_text.split("-")
    return PRIVATE_REPO_ROOT / "journal" / "summaries" / year / month / f"{day_text}_Summary.md"


def candidate_path_for(day_text: str) -> Path:
    return CANDIDATES_DIR / f"{day_text}.jsonl"


def load_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    items: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                items.append(value)
    return items


def refresh_recent_candidates(anchor: str, days: int, *, also_docs: bool) -> list[str]:
    outputs: list[str] = []
    env = dict(os.environ)
    env.setdefault("LIFEREPO_PRIVATE_ROOT", str(PRIVATE_REPO_ROOT))
    for day_text in iter_dates(anchor, days):
        summary_path = summary_path_for(day_text)
        if not summary_path.exists():
            outputs.append(f"- {day_text}: skipped (no summary)")
            continue
        cmd = [sys.executable, str(EXTRACT_SCRIPT), "--date", day_text]
        if also_docs:
            cmd.append("--also-docs")
        proc = subprocess.run(
            cmd,
            cwd=PRIVATE_REPO_ROOT,
            text=True,
            capture_output=True,
            env=env,
        )
        line = proc.stdout.strip() or proc.stderr.strip() or f"{day_text}: exit {proc.returncode}"
        outputs.append(f"- {line}")
    return outputs


def run_validation() -> tuple[bool, str]:
    env = dict(os.environ)
    env.setdefault("LIFEREPO_PRIVATE_ROOT", str(PRIVATE_REPO_ROOT))
    proc = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT)],
        cwd=PRIVATE_REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
    )
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def accepted_index() -> dict[tuple[str, str], list[dict[str, object]]]:
    index: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record_type, path in CANONICAL_FILES.items():
        for record in load_jsonl(path):
            index[(record_type, normalize(str(record.get("summary", ""))))].append(record)
    return index


def recent_candidate_records(anchor: str, lookback_days: int) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for day_text in iter_dates(anchor, lookback_days):
        path = candidate_path_for(day_text)
        for record in load_jsonl(path):
            enriched = dict(record)
            enriched["_candidate_file"] = path.relative_to(PRIVATE_REPO_ROOT).as_posix()
            records.append(enriched)
    return records


def cluster_records(records: Iterable[dict[str, object]]) -> dict[tuple[str, str], list[dict[str, object]]]:
    clusters: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        key = (str(record.get("type", "")), normalize(str(record.get("summary", ""))))
        if key[1]:
            clusters[key].append(record)
    return clusters


def report_path_for(anchor: str, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR / f"{anchor}_dream.md"


def report_doc_id(target: Path) -> str:
    """Build a portable doc id from the configured repo and report path."""
    resolved_target = target.expanduser().resolve()
    try:
        relative = resolved_target.relative_to(PRIVATE_REPO_ROOT.resolve())
    except ValueError:
        relative = Path("memory") / "reports" / resolved_target.name
    return f"{PRIVATE_REPO_ROOT.name}/{relative.with_suffix('').as_posix()}"


def render_report(
    *,
    anchor: str,
    refreshed_lines: list[str],
    validation_ok: bool,
    validation_output: str,
    recent_records: list[dict[str, object]],
    doc_id: str,
) -> str:
    by_type = Counter(str(record.get("type", "")) for record in recent_records)
    accepted = accepted_index()
    clusters = cluster_records(recent_records)

    recurring: list[tuple[tuple[str, str], list[dict[str, object]]]] = []
    reinforcement: list[tuple[dict[str, object], list[dict[str, object]]]] = []
    stale_commitments: list[dict[str, object]] = []

    for key, items in clusters.items():
        record_type, _ = key
        unique_days = sorted({str(item.get("date", "")) for item in items})
        if len(unique_days) >= 2:
            recurring.append((key, items))
        if key in accepted:
            reinforcement.append((accepted[key][0], items))

    for record in recent_records:
        if record.get("type") != "commitment":
            continue
        record_date = str(record.get("date", ""))
        if record_date and record_date <= (datetime.strptime(anchor, "%Y-%m-%d").date() - timedelta(days=3)).isoformat():
            stale_commitments.append(record)

    recurring.sort(key=lambda pair: len({str(item.get("date", "")) for item in pair[1]}), reverse=True)
    reinforcement.sort(key=lambda pair: len(pair[1]), reverse=True)
    stale_commitments.sort(key=lambda item: str(item.get("date", "")))

    lines: list[str] = []
    lines.append("---")
    lines.append('doc_schema: "doc-frontmatter-v1"')
    lines.append(f'doc_id: "{doc_id}"')
    lines.append('doc_type: "memory_report"')
    lines.append('doc_status: "active"')
    lines.append(f'title: "Memory Dream Report - {anchor}"')
    lines.append('memory_eligible: false')
    lines.append("---")
    lines.append("")
    lines.append(f"# Memory Dream Report - {anchor}")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Recent pending candidates scanned: {len(recent_records)}")
    lines.append(f"- Pending by type: {', '.join(f'{key}={value}' for key, value in sorted(by_type.items())) or 'none'}")
    lines.append(f"- Validation status: {'ok' if validation_ok else 'needs attention'}")
    lines.append("- This is a deterministic maintenance pass, not an LLM rewrite. It refreshes extraction, checks record shape, and leaves a review inbox.")
    lines.append("")
    lines.append("## Recent Refresh")
    lines.append("")
    lines.extend(refreshed_lines or ["- No refresh steps ran."])
    lines.append("")
    lines.append("## Review First")
    lines.append("")
    if recurring:
        for (_, _), items in recurring[:10]:
            sample = items[0]
            dates = ", ".join(sorted({str(item.get("date", "")) for item in items}))
            lines.append(f"- [{sample.get('type')}] {sample.get('summary')}  ")
            lines.append(f"  Seen on: {dates}. Candidate ids: {', '.join(str(item.get('id', '')) for item in items[:4])}")
    else:
        lines.append("- No repeated recent candidate signals yet.")
    lines.append("")
    lines.append("## Reinforce Existing Memory")
    lines.append("")
    if reinforcement:
        for accepted_record, items in reinforcement[:10]:
            lines.append(f"- {accepted_record.get('id')}: {accepted_record.get('summary')}  ")
            lines.append(f"  Reinforced by: {', '.join(str(item.get('id', '')) for item in items[:4])}")
    else:
        lines.append("- No recent candidates matched accepted memory strongly enough to suggest reinforcement.")
    lines.append("")
    lines.append("## Aging Commitments")
    lines.append("")
    if stale_commitments:
        for record in stale_commitments[:10]:
            lines.append(f"- {record.get('date')}: {record.get('summary')} (`{record.get('id')}`)")
    else:
        lines.append("- No older unreviewed commitments crossed the aging threshold.")
    lines.append("")
    lines.append("## Validation Output")
    lines.append("")
    if validation_output:
        lines.append("```text")
        lines.append(validation_output)
        lines.append("```")
    else:
        lines.append("- No validation output.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    refreshed_lines = refresh_recent_candidates(
        args.date,
        args.refresh_days,
        also_docs=not args.skip_docs,
    )
    validation_ok, validation_output = run_validation()
    recent_records = recent_candidate_records(args.date, args.lookback_days)
    target = report_path_for(args.date, args.report_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_report(
            anchor=args.date,
            refreshed_lines=refreshed_lines,
            validation_ok=validation_ok,
            validation_output=validation_output,
            recent_records=recent_records,
            doc_id=report_doc_id(target),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {target}")
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
