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
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

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
WORKSPACE_ROOT = ROOT.parent
GEORGE_LLM_WIKI_ROOT = WORKSPACE_ROOT / "GeorgeLLMWiki"
GEORGE_LLM_WIKI_INGEST = GEORGE_LLM_WIKI_ROOT / "scripts" / "ingest_workspace_docs.py"
CAPTURES_DIR = ROOT / "captures"
NOTES_LAST_EXPORT_MARKER = CAPTURES_DIR / "apple-notes" / "all-notes" / ".last_export"
EMAIL_DIR = CAPTURES_DIR / "email"
CALENDAR_DIR = CAPTURES_DIR / "calendar"
CALENDAR_LOG = CALENDAR_DIR / "export.log"
CALENDAR_WEEKLY = CALENDAR_DIR / "weekly_calendar.md"
PREP_MARKERS_DIR = ROOT / "journal" / ".workflow_prep_markers"
CONVERSATION_NOTES_DIR = CAPTURES_DIR / "audio-conversations" / "notes"
DEFAULT_EXPORT_FRESHNESS_SECONDS = 300
DEFAULT_AUDIO_LLM_PROVIDER = "gemini"
DEFAULT_AUDIO_LLM_MODEL = "gemini-2.5-flash"
RETRYABLE_HTTP_CODES = {429, 500, 503}
DJI_TRANSCRIPTS_ROOT = ROOT / "journal" / "audio" / "transcripts"
SNACKVOICE_APP_SUPPORT_ID = os.environ.get("SNACKVOICE_APP_SUPPORT_ID", "com.example.snackvoice")
SNACKVOICE_AMBIENT_CAPTURE_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / SNACKVOICE_APP_SUPPORT_ID
    / "ambient-capture"
)

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
    "Audio Log",
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


@dataclass(frozen=True)
class AudioSourceSnapshot:
    dji_transcripts: list[Path]
    ambient_capture_file: Path | None
    ambient_capture_segments: int


@dataclass(frozen=True)
class AudioSegment:
    source_type: str
    source_label: str
    time_range: str
    text: str


@dataclass(frozen=True)
class AudioSummaryConfig:
    provider: str
    model: str
    allow_fallback: bool


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


def read_marker_payload(name: str) -> dict[str, object] | None:
    path = _prep_marker_path(name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def write_marker_payload(name: str, payload: dict[str, object]) -> None:
    PREP_MARKERS_DIR.mkdir(parents=True, exist_ok=True)
    enriched = dict(payload)
    enriched["completed_at"] = _now_utc().isoformat()
    _prep_marker_path(name).write_text(json.dumps(enriched, indent=2) + "\n", encoding="utf-8")


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


def git_head_sha() -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha or None


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
    notes_dir = CAPTURES_DIR / "apple-notes" / "all-notes"
    return len(list(notes_dir.glob(f"{day_text}_*")))


def email_count_for(day_text: str) -> int:
    email_dir = CAPTURES_DIR / "email"
    return len(list(email_dir.glob(f"**/{day_text}_*")))


def reflection_exists_for(day_text: str) -> bool:
    return (ROOT / "journal" / "reflections" / f"{day_text}_Thoughts.md").exists()


def conversation_note_paths_for(day_text: str) -> list[Path]:
    year, month, _ = day_text.split("-")
    month_dir = CONVERSATION_NOTES_DIR / year / month
    if not month_dir.exists():
        return []
    return sorted(month_dir.glob(f"{day_text}-*.md"))


def dji_transcripts_for(day_text: str) -> list[Path]:
    year, month, _ = day_text.split("-")
    day_token = day_text.replace("-", "")
    month_dir = DJI_TRANSCRIPTS_ROOT / year / month
    if not month_dir.exists():
        return []
    return sorted(month_dir.glob(f"*{day_token}*_transcript.md"))


def ambient_capture_file_for(day_text: str) -> Path | None:
    candidate = SNACKVOICE_AMBIENT_CAPTURE_DIR / f"{day_text}.md"
    if candidate.exists():
        return candidate
    return None


def ambient_capture_segment_count(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return len(re.findall(r"^##\s+\d", text, flags=re.MULTILINE))


def audio_source_snapshot(day_text: str) -> AudioSourceSnapshot:
    ambient_file = ambient_capture_file_for(day_text)
    return AudioSourceSnapshot(
        dji_transcripts=dji_transcripts_for(day_text),
        ambient_capture_file=ambient_file,
        ambient_capture_segments=ambient_capture_segment_count(ambient_file) if ambient_file else 0,
    )


def print_audio_sources(day_text: str) -> AudioSourceSnapshot:
    snapshot = audio_source_snapshot(day_text)
    print("\n== Audio sources ==")
    if snapshot.dji_transcripts:
        print(
            "- DJI transcripts:"
            f" {len(snapshot.dji_transcripts)} file(s) under"
            f" {snapshot.dji_transcripts[0].parent}"
        )
        for path in snapshot.dji_transcripts[:5]:
            print(f"  - {path.name}")
        remaining = len(snapshot.dji_transcripts) - 5
        if remaining > 0:
            print(f"  - … {remaining} more")
    else:
        print(f"- DJI transcripts: none found under {DJI_TRANSCRIPTS_ROOT}")

    if snapshot.ambient_capture_file is not None:
        size_kb = snapshot.ambient_capture_file.stat().st_size / 1024
        print(
            "- SnackVoice ambient capture:"
            f" {snapshot.ambient_capture_segments} segment(s),"
            f" {size_kb:.1f} KB,"
            f" {snapshot.ambient_capture_file}"
        )
    else:
        print(
            "- SnackVoice ambient capture:"
            f" none found at {SNACKVOICE_AMBIENT_CAPTURE_DIR / f'{day_text}.md'}"
        )

    return snapshot


def normalize_transcript_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    cleaned = " ".join(line for line in lines if line)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def transcript_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def looks_low_signal_transcript(text: str) -> bool:
    normalized = normalize_transcript_text(text)
    if not normalized:
        return True

    tokens = transcript_tokens(normalized)
    if len(tokens) < 12:
        return True

    unique_ratio = len(set(tokens)) / max(len(tokens), 1)
    if unique_ratio < 0.22:
        return True

    repeated_thanks = normalized.lower().count("thank you")
    if repeated_thanks >= 3:
        return True

    low_signal_markers = (
        "beadaholique",
        "subscribe to my channel",
        "thanks for watching",
        "foreign foreign foreign",
        "grandpa grandpa",
    )
    if any(marker in normalized.lower() for marker in low_signal_markers):
        return True

    return False


def parse_ambient_capture_segments(path: Path) -> list[AudioSegment]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    pattern = re.compile(
        r"^##\s+(?P<start>.+?)\s*-\s*(?P<end>.+?)\s*$\n(?P<body>.*?)(?=^##\s+.+?\s*-\s*.+?\s*$|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    segments: list[AudioSegment] = []
    for match in pattern.finditer(text):
        start = match.group("start").strip()
        end = match.group("end").strip()
        body = normalize_transcript_text(match.group("body"))
        if looks_low_signal_transcript(body):
            continue
        segments.append(
            AudioSegment(
                source_type="ambient",
                source_label="Ambient capture",
                time_range=f"{start}-{end}",
                text=body,
            )
        )
    return segments


def parse_dji_transcript_segments(paths: list[Path]) -> list[AudioSegment]:
    segments: list[AudioSegment] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        body = normalize_transcript_text(text)
        if looks_low_signal_transcript(body):
            continue
        segments.append(
            AudioSegment(
                source_type="dji",
                source_label=path.stem,
                time_range=path.stem,
                text=body,
            )
        )
    return segments


def _clock_to_minutes(raw: str) -> int | None:
    cleaned = raw.strip().upper()
    try:
        parsed = datetime.strptime(cleaned, "%I:%M %p")
    except ValueError:
        try:
            parsed = datetime.strptime(cleaned, "%H:%M")
        except ValueError:
            return None
    return parsed.hour * 60 + parsed.minute


def merge_audio_segments(segments: list[AudioSegment]) -> list[AudioSegment]:
    if not segments:
        return []

    merged: list[AudioSegment] = []
    current = segments[0]
    if current.source_type == "ambient" and "-" in current.time_range:
        current_start, current_end = [part.strip() for part in current.time_range.split("-", 1)]
        current_end_min = _clock_to_minutes(current_end)
    else:
        current_start = current.time_range
        current_end_min = None

    for segment in segments[1:]:
        seg_start = segment.time_range
        seg_end = segment.time_range
        seg_start_min = None
        seg_end_min = None
        if segment.source_type == "ambient" and "-" in segment.time_range:
            seg_start, seg_end = [part.strip() for part in segment.time_range.split("-", 1)]
            seg_start_min = _clock_to_minutes(seg_start)
            seg_end_min = _clock_to_minutes(seg_end)
        can_merge = (
            current.source_type == "ambient"
            and segment.source_type == "ambient"
            and current_end_min is not None
            and seg_start_min is not None
            and 0 <= seg_start_min - current_end_min <= 3
            and len(current.text) + len(segment.text) <= 2200
        )
        if can_merge:
            current = AudioSegment(
                source_type="ambient",
                source_label="Ambient capture",
                time_range=f"{current_start}-{seg_end}",
                text=f"{current.text} {segment.text}".strip(),
            )
            current_end_min = seg_end_min
            continue

        merged.append(current)
        current = segment
        current_start = seg_start
        current_end_min = seg_end_min

    merged.append(current)
    return merged


def build_audio_segments(day_text: str) -> list[AudioSegment]:
    snapshot = audio_source_snapshot(day_text)
    segments = parse_dji_transcript_segments(snapshot.dji_transcripts)
    if snapshot.ambient_capture_file is not None:
        segments.extend(parse_ambient_capture_segments(snapshot.ambient_capture_file))
    return merge_audio_segments(segments)


def fallback_tag_guess(text: str) -> list[str]:
    lowered = text.lower()
    tags: list[str] = []
    keyword_map = {
        "work": ("work", "databricks", "team", "s3", "bucket"),
        "workflow": ("workflow", "process", "automation", "memory"),
        "product": ("product", "feature", "app", "shipping", "posting"),
        "marketing": ("marketing", "linkedin", "x ", "twitter", "social", "post"),
        "people": ("people", "friend", "teresa", "someone"),
        "meta": ("meta", "philosophy", "thinking"),
        "career": ("career", "job", "interview"),
    }
    for tag, markers in keyword_map.items():
        if any(marker in lowered for marker in markers):
            tags.append(tag)
    return tags[:3] or ["work"]


def score_segment_priority(segment: AudioSegment) -> tuple[int, int]:
    text = segment.text
    tags = fallback_tag_guess(text)
    score = 0
    if segment.source_type == "ambient":
        score += 2
    if "workflow" in tags:
        score += 3
    if "product" in tags or "marketing" in tags:
        score += 2
    if "people" in tags:
        score += 1
    score += min(len(text) // 180, 4)
    return score, len(text)


def summarize_segment_text(text: str, *, max_words: int = 40, max_chars: int = 260) -> str:
    normalized = normalize_transcript_text(text)
    if not normalized:
        return ""

    sentences = re.split(r"(?<=[.!?。！？])\s+", normalized)
    meaningful = [sentence.strip() for sentence in sentences if sentence.strip()]
    if meaningful:
        summary = " ".join(meaningful[:2]).strip()
    else:
        summary = normalized

    words = summary.split()
    if len(words) > max_words:
        summary = " ".join(words[:max_words]).rstrip(",;:") + "..."
    if len(summary) > max_chars:
        summary = summary[: max_chars - 3].rstrip(",;: ") + "..."
    return summary


def normalized_dedup_key(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def gemini_api_key() -> str | None:
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def audio_summary_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "overall_takeaway": {"type": "string"},
            "audio_log_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "time_range": {"type": "string"},
                        "source_label": {"type": "string"},
                        "summary": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["time_range", "source_label", "summary", "tags"],
                },
            },
            "key_decisions": {"type": "array", "items": {"type": "string"}},
            "people_relationships": {"type": "array", "items": {"type": "string"}},
            "conversation_milestones": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "overall_takeaway",
            "audio_log_items",
            "key_decisions",
            "people_relationships",
            "conversation_milestones",
        ],
    }


def audio_summary_system_instruction() -> str:
    return (
        "You are interpreting same-day personal audio transcripts for a daily journal workflow. "
        "Your job is to convert noisy ambient or DJI transcript segments into a compact, useful day-level synthesis. "
        "Repair obvious ASR mistakes when the meaning is clear, but do not invent details. "
        "Prefer thematic summaries over transcript snippets. "
        "Call out uncertainty plainly when needed. "
        "If content is mostly background media, say that directly instead of pretending it is a conversation. "
        "If a segment is personal logistics or care for family, preserve that human context. "
        "Return concise JSON that matches the schema exactly."
    )


def _trim_audio_text(text: str, *, limit: int = 900) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def build_audio_model_prompt(day_text: str, segments: list[AudioSegment]) -> str:
    prompt = {
        "date": day_text,
        "task": [
            "Summarize the audio properly.",
            "Use thematic interpretation, not transcript passthrough.",
            "Group nearby snippets into a few meaningful items.",
            "Pull up decisions, people context, and work milestones when they are actually supported.",
            "If a segment is too noisy, say what is still inferable instead of copying gibberish.",
        ],
        "tag_vocabulary": [
            "workflow",
            "people",
            "health",
            "travel",
            "work",
            "personal",
            "meta",
            "career",
            "product",
            "content",
        ],
        "output_rules": [
            "Return at most 6 audio_log_items.",
            "Each item summary should be concrete and readable, usually 1-3 sentences.",
            "Do not quote long raw transcript fragments unless a short phrase is necessary.",
            "Prefer best-guess interpretation with uncertainty markers over nonsense text.",
            "key_decisions, people_relationships, and conversation_milestones should be bullets ready to insert into markdown sections without a leading '- '.",
        ],
        "segments": [
            {
                "time_range": segment.time_range,
                "source_label": segment.source_label,
                "source_type": segment.source_type,
                "text": _trim_audio_text(segment.text),
            }
            for segment in segments[:18]
        ],
    }
    return json.dumps(prompt, indent=2, ensure_ascii=False)


def gemini_generate_json(
    *,
    api_key: str,
    model: str,
    prompt: str,
    schema: dict[str, Any],
    max_attempts: int = 4,
) -> dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "system_instruction": {
            "parts": [{"text": audio_summary_system_instruction()}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "temperature": 0.2,
        },
    }
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "x-goog-api-client": "georgeskills-journal-ops/0.1",
        },
        method="POST",
    )
    body = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read().decode("utf-8")
                break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in RETRYABLE_HTTP_CODES and attempt < max_attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
                continue
            raise RuntimeError(f"Gemini API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
                continue
            raise RuntimeError(f"Gemini API request failed: {exc}") from exc

    if body is None:
        raise RuntimeError("Gemini API request failed after retries.")

    parsed = json.loads(body)
    candidates = parsed.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini API returned no candidates: {body}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise RuntimeError(f"Gemini API returned empty text: {body}")
    return json.loads(text)


def run_audio_summary_model(*, provider: str, model: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    if provider != "gemini":
        raise RuntimeError(f"Unsupported audio summary provider: {provider}")
    api_key = gemini_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing Gemini API key for audio interpretation. Set GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_GENERATIVE_AI_API_KEY."
        )
    return gemini_generate_json(api_key=api_key, model=model, prompt=prompt, schema=schema)


def _normalize_audio_tags(tags: list[Any]) -> list[str]:
    allowed = {"workflow", "people", "health", "travel", "work", "personal", "meta", "career", "product", "content"}
    cleaned: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = str(tag).strip().lower().strip("[]")
        if normalized not in allowed or normalized in seen:
            continue
        cleaned.append(normalized)
        seen.add(normalized)
    return cleaned[:3]


def normalize_audio_payload(payload: dict[str, Any], *, segments: list[AudioSegment]) -> dict[str, Any]:
    segment_lookup = {(segment.time_range, segment.source_label): segment for segment in segments}
    items: list[dict[str, Any]] = []
    for raw_item in list(payload.get("audio_log_items", []))[:6]:
        if not isinstance(raw_item, dict):
            continue
        time_range = str(raw_item.get("time_range", "")).strip()
        source_label = str(raw_item.get("source_label", "")).strip()
        summary = " ".join(str(raw_item.get("summary", "")).split()).strip()
        if not summary:
            continue
        if not time_range or not source_label:
            matched = next(iter(segment_lookup.values()), None)
            if matched is not None:
                time_range = time_range or matched.time_range
                source_label = source_label or matched.source_label
        if not time_range:
            continue
        items.append(
            {
                "time_range": time_range,
                "source_label": source_label or "Ambient capture",
                "summary": summary,
                "tags": _normalize_audio_tags(list(raw_item.get("tags", []))),
            }
        )

    if not items:
        raise RuntimeError("Audio summary model returned no usable audio_log_items.")

    def _normalize_lines(value: Any, *, limit: int) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in list(value or [])[:limit]:
            text = " ".join(str(item).split()).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text.removeprefix("- ").strip())
        return normalized

    return {
        "audio_log_items": items,
        "key_decisions": _normalize_lines(payload.get("key_decisions"), limit=4),
        "people_relationships": _normalize_lines(payload.get("people_relationships"), limit=4),
        "conversation_milestones": _normalize_lines(payload.get("conversation_milestones"), limit=5),
        "overall_takeaway": " ".join(str(payload.get("overall_takeaway", "")).split()).strip(),
    }


def promoted_bullets_from_items(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    milestones: list[str] = []
    decisions: list[str] = []
    people: list[str] = []
    seen: set[str] = set()

    for item in items:
        summary = str(item.get("summary", "")).strip()
        if not summary:
            continue
        if len(summary) > 180:
            continue
        tags = {tag.strip("[] ").strip().lower() for tag in item.get("tags", []) if str(tag).strip()}
        time_range = str(item.get("time_range", "")).strip()
        time_prefix = f"`{time_range}` " if time_range else ""
        lowered = summary.lower()
        if lowered.startswith("hey, how are you") or lowered.startswith("i'm good, how are you"):
            continue
        if lowered in seen:
            continue
        seen.add(lowered)

        if "people" in tags and len(summary.split()) >= 10 and "product" not in tags:
            people.append(f"{time_prefix}{summary}")
        if {"workflow", "work", "product", "career"} & tags and len(summary.split()) >= 8:
            milestones.append(f"{time_prefix}{summary}")
        if (
            "decision" in lowered
            or "plan" in lowered
            or "next" in lowered
            or "onboarding" in lowered
            or "architecture" in lowered
            or "databricks" in lowered
        ):
            decisions.append(f"{time_prefix}{summary}")

    return {
        "Conversation Milestones": milestones[:4],
        "Key Decisions": decisions[:3],
        "People / Relationships": people[:3],
    }


def fallback_audio_summary(segments: list[AudioSegment]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    scored_segments = sorted(segments, key=score_segment_priority, reverse=True)
    for segment in scored_segments[:14]:
        summary_text = summarize_segment_text(segment.text)
        if not summary_text:
            continue
        dedup_key = normalized_dedup_key(summary_text)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        items.append(
            {
                "time_range": segment.time_range,
                "source_label": segment.source_label,
                "summary": summary_text,
                "tags": fallback_tag_guess(segment.text),
            }
        )
    items.sort(key=lambda item: _clock_to_minutes(str(item.get("time_range", "")).split("-", 1)[0].strip()) or 0)
    promoted = promoted_bullets_from_items(items)
    return {
        "audio_log_items": items,
        "key_decisions": promoted["Key Decisions"],
        "people_relationships": promoted["People / Relationships"],
        "conversation_milestones": promoted["Conversation Milestones"],
        "overall_takeaway": "Audio sources were ingested directly from the transcript artifacts and condensed into a cleaned deterministic pass for the daily log.",
    }


def summarize_audio_segments(
    day_text: str,
    segments: list[AudioSegment],
    *,
    config: AudioSummaryConfig,
) -> tuple[dict[str, Any], str]:
    prompt = build_audio_model_prompt(day_text, segments)
    try:
        payload = run_audio_summary_model(
            provider=config.provider,
            model=config.model,
            prompt=prompt,
            schema=audio_summary_schema(),
        )
        return normalize_audio_payload(payload, segments=segments), "llm"
    except Exception:
        if not config.allow_fallback:
            raise
        return fallback_audio_summary(segments), "deterministic"


def _format_tags(tags: list[str]) -> str:
    cleaned = [tag.strip("[] ").strip() for tag in tags if tag.strip("[] ").strip()]
    return "".join(f"[{tag}]" for tag in cleaned)


def render_audio_log(day_text: str, payload: dict[str, Any]) -> str:
    items = list(payload.get("audio_log_items", []))
    if not items:
        return "- No meaningful audio artifacts were ingested for this date."

    lines: list[str] = []
    for item in items:
        time_range = str(item.get("time_range", "")).strip() or day_text
        source_label = str(item.get("source_label", "")).strip()
        summary = str(item.get("summary", "")).strip()
        tags = _format_tags(list(item.get("tags", [])))
        prefix = f"- `{time_range}`"
        if source_label and source_label != "Ambient capture":
            prefix += f" — `{source_label}`"
        prefix += " — "
        line = prefix + summary
        if tags:
            line += f" {tags}"
        lines.append(line)

    overall_takeaway = str(payload.get("overall_takeaway", "")).strip()
    if overall_takeaway:
        lines.append(f"- Best overall interpretation: {overall_takeaway}")
    return "\n".join(lines)


def build_wiki_ingest_state(*, target_date: str, summary_path: Path) -> dict[str, object] | None:
    if not summary_path.exists() or not GEORGE_LLM_WIKI_ROOT.exists():
        return None

    wiki_files = [
        path
        for path in GEORGE_LLM_WIKI_ROOT.rglob("*.md")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    ]
    state = build_post_step_state(target_date=target_date, summary_path=summary_path, include_git_head=True)
    if state is None:
        return None
    state["wiki_markdown_count"] = len(wiki_files)
    state["wiki_markdown_max_mtime_ns"] = max((path.stat().st_mtime_ns for path in wiki_files), default=None)
    return state


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


def build_post_step_state(
    *,
    target_date: str,
    summary_path: Path,
    include_git_head: bool = False,
    extra_paths: list[Path] | None = None,
) -> dict[str, object] | None:
    if not summary_path.exists():
        return None

    state: dict[str, object] = {
        "target_date": target_date,
        "summary_path": str(summary_path),
        "summary_mtime_ns": summary_path.stat().st_mtime_ns,
    }

    if include_git_head:
        state["git_head_sha"] = git_head_sha()

    paths = [path for path in (extra_paths or []) if path.exists()]
    state["extra_path_count"] = len(paths)
    state["extra_path_max_mtime_ns"] = max((path.stat().st_mtime_ns for path in paths), default=None)
    return state


def maybe_skip_cached_post_step(name: str, marker_name: str, state: dict[str, object] | None) -> StepResult | None:
    if state is None:
        return None

    previous = read_marker_payload(marker_name)
    if previous is None:
        return None

    comparable_keys = tuple(state.keys())
    if any(previous.get(key) != state.get(key) for key in comparable_keys):
        return None

    print(f"\n== {name} ==")
    print("skipped (inputs unchanged since last successful run)")
    return StepResult(name=name, ok=True, detail="skipped (inputs unchanged)")


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


def append_unique_bullets_to_section(text: str, title: str, bullets: list[str]) -> str:
    normalized_new = [bullet.strip() for bullet in bullets if bullet.strip()]
    if not normalized_new:
        return text

    frontmatter, markdown_body = split_frontmatter(text)
    sections = extract_level2_headers(markdown_body)
    existing_bullets: list[str] = []
    if title in sections:
        start, end = sections[title]
        section_body = markdown_body[start:end]
        existing_bullets = re.findall(r"^- (.+)$", section_body, flags=re.MULTILINE)

    merged = list(existing_bullets)
    existing_norm = {bullet.strip().lower() for bullet in existing_bullets}
    for bullet in normalized_new:
        candidate = bullet.removeprefix("- ").strip()
        if candidate.lower() in existing_norm:
            continue
        merged.append(candidate)
        existing_norm.add(candidate.lower())

    body = "\n".join(f"- {bullet}" for bullet in merged) if merged else "- Not logged yet."
    return upsert_level2_section(text, title, body)


def build_audio_sections(day_text: str, *, config: AudioSummaryConfig) -> tuple[str | None, dict[str, list[str]], str | None]:
    segments = build_audio_segments(day_text)
    if not segments:
        return None, {}, None

    payload, mode = summarize_audio_segments(day_text, segments, config=config)
    promoted = {
        "Key Decisions": [str(item).strip() for item in payload.get("key_decisions", []) if str(item).strip()],
        "People / Relationships": [
            str(item).strip() for item in payload.get("people_relationships", []) if str(item).strip()
        ],
        "Conversation Milestones": [
            str(item).strip() for item in payload.get("conversation_milestones", []) if str(item).strip()
        ],
    }
    return render_audio_log(day_text, payload), promoted, mode


def hydrate_summary_context(day_text: str, *, audio_config: AudioSummaryConfig) -> StepResult:
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

    try:
        audio_body, promoted_audio, audio_mode = build_audio_sections(day_text, config=audio_config)
    except Exception as exc:
        return StepResult("Summary context sync", False, f"audio interpretation required: {exc}")
    if audio_body:
        updated = upsert_level2_section(updated, f"Audio Log — {day_text}", audio_body)
        changed_sections.append(f"Audio Log ({audio_mode or 'generated'})")
        for section_title, bullets in promoted_audio.items():
            before_section = updated
            updated = append_unique_bullets_to_section(updated, section_title, bullets)
            if updated != before_section:
                changed_sections.append(section_title)

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
        help="Skip derived wiki refresh for the GeorgeLLMWiki layer.",
    )
    parser.add_argument(
        "--allow-health-miss",
        action="store_true",
        help="Return success even when no health source is available",
    )
    parser.add_argument(
        "--audio-llm-provider",
        default=DEFAULT_AUDIO_LLM_PROVIDER,
        choices=["gemini"],
        help="Provider used for required audio interpretation when audio artifacts exist.",
    )
    parser.add_argument(
        "--audio-llm-model",
        default=os.environ.get("JOURNAL_AUDIO_LLM_MODEL", DEFAULT_AUDIO_LLM_MODEL),
        help="Model used for audio interpretation.",
    )
    parser.add_argument(
        "--allow-audio-fallback",
        action="store_true",
        help="Allow deterministic audio fallback instead of failing when model-based audio interpretation is unavailable.",
    )
    args = parser.parse_args()

    audio_config = AudioSummaryConfig(
        provider=args.audio_llm_provider,
        model=args.audio_llm_model,
        allow_fallback=args.allow_audio_fallback,
    )

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

    results.append(hydrate_summary_context(args.date, audio_config=audio_config))
    results.append(run_step("Workflow completeness", ["python3", str(CHECK_COMPLETENESS), "--date", args.date], ok_codes={0, 1}))

    summary_path = summary_path_for(args.date)
    post_summary_specs: list[ParallelStepSpec] = []
    post_summary_states: list[tuple[str, dict[str, object]]] = []

    if not args.skip_memory:
        if summary_path.exists():
            memory_cmd = ["python3", str(MEMORY_EXTRACT), "--date", args.date]
            if not args.skip_doc_memory:
                memory_cmd.append("--also-docs")

            memory_state = build_post_step_state(
                target_date=args.date,
                summary_path=summary_path,
                include_git_head=not args.skip_doc_memory,
            )
            skipped = maybe_skip_cached_post_step("Memory candidate refresh", "memory_refresh", memory_state)
            if skipped is not None:
                results.append(skipped)
            else:
                post_summary_specs.append(
                    ParallelStepSpec(
                        "Memory candidate refresh",
                        memory_cmd,
                    )
                )
                if memory_state is not None:
                    post_summary_states.append(("memory_refresh", memory_state))
        else:
            print("\n== Memory candidate refresh ==")
            print("Skipped: summary file does not exist yet.")

    if not args.skip_agent_managed:
        if summary_path.exists() and GEORGE_LLM_WIKI_INGEST.exists():
            wiki_state = build_wiki_ingest_state(target_date=args.date, summary_path=summary_path)
            skipped = maybe_skip_cached_post_step(
                "GeorgeLLMWiki ingest refresh",
                "george_llm_wiki_refresh",
                wiki_state,
            )
            if skipped is not None:
                results.append(skipped)
            else:
                post_summary_specs.append(
                    ParallelStepSpec(
                        "GeorgeLLMWiki ingest refresh",
                        [
                            "python3",
                            str(GEORGE_LLM_WIKI_INGEST),
                        ],
                    )
                )
                if wiki_state is not None:
                    post_summary_states.append(("george_llm_wiki_refresh", wiki_state))
        elif not GEORGE_LLM_WIKI_INGEST.exists():
            print("\n== GeorgeLLMWiki ingest refresh ==")
            print("Skipped: GeorgeLLMWiki ingest script is not available yet.")
        else:
            print("\n== GeorgeLLMWiki ingest refresh ==")
            print("Skipped: summary file does not exist yet.")

    if post_summary_specs:
        post_summary_results = run_steps_parallel(post_summary_specs)
        results.extend(post_summary_results)
        for (marker_name, state), result in zip(post_summary_states, post_summary_results):
            if result.ok:
                write_marker_payload(marker_name, state)

    print("\n== Context snapshot ==")
    print(f"- Summary exists: {'yes' if summary_path.exists() else 'no'}")
    print(f"- Apple Notes for date: {note_count_for(args.date)}")
    print(f"- Emails for date: {email_count_for(args.date)}")
    print(f"- Reflection exists: {'yes' if reflection_exists_for(args.date) else 'no'}")
    print_audio_sources(args.date)

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
