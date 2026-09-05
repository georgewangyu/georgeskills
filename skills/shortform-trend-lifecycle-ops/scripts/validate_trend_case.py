#!/usr/bin/env python3
"""Validate a short-form trend lifecycle case and its evidence JSONL."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_KEYS = {
    "trend_case_schema",
    "trend_id",
    "title",
    "discovered_on",
    "snapshot_at",
    "platforms",
    "earliest_source_backed_at",
    "first_breakout_at",
    "copy_wave_onset_at",
    "peak_at",
    "decay_onset_at",
    "current_stage",
    "usable_window",
    "confidence",
}
REQUIRED_SECTIONS = (
    "## Decision",
    "## Format Grammar",
    "## Lifecycle Card",
    "## Observed Evidence",
    "## Source and Credit Lineage",
    "## Replication and Velocity",
    "## Remaining Usable Window",
    "## Adaptation Boundary",
    "## Inference",
    "## Confidence and Gaps",
    "## Collection Receipt",
)
STAGES = {
    "seed",
    "emerging",
    "accelerating",
    "peaking",
    "saturating",
    "decaying",
    "dormant",
    "reviving",
    "platform-split",
    "unknown",
}
WINDOWS = {
    "act-now",
    "adapt-with-mutation",
    "watch",
    "direct-copy-exhausted",
    "unknown",
}
ROLES = {
    "source_candidate",
    "breakout_mutation",
    "independent_copy",
    "parent_ancestor",
    "negative_control",
    "metric_snapshot",
}
MATCHES = {"confirmed", "probable", "rejected"}
EVIDENCE_KEYS = {
    "evidence_id",
    "platform",
    "url",
    "creator",
    "published_at",
    "observed_at",
    "role",
    "format_match",
    "source_class",
}
METRICS = ("views", "likes", "comments", "shares", "followers")
CONFIDENCE = {"low", "medium", "high"}
TREND_ID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_([a-z0-9]+(?:-[a-z0-9]+)*)$")
MILESTONE_FIELDS = (
    "earliest_source_backed_at",
    "first_breakout_at",
    "copy_wave_onset_at",
    "peak_at",
    "decay_onset_at",
)
NONEMPTY_CASE_FIELDS = {
    "trend_case_schema",
    "trend_id",
    "title",
    "discovered_on",
    "snapshot_at",
    "platforms",
    "current_stage",
    "usable_window",
    "confidence",
}
NONEMPTY_EVIDENCE_FIELDS = {
    "evidence_id",
    "platform",
    "url",
    "creator",
    "observed_at",
    "role",
    "format_match",
    "source_class",
}


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line.startswith((" ", "\t", "#")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = unquote(value)
    return fields


def valid_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_date(value: object) -> bool:
    if not nonempty_string(value) or "T" in value:
        return False
    try:
        dt.date.fromisoformat(value.strip())
        return True
    except ValueError:
        return False


def valid_date_or_datetime(value: object, *, require_timezone: bool = False) -> bool:
    if not nonempty_string(value):
        return False
    normalized = value.strip()
    try:
        if "T" not in normalized:
            dt.date.fromisoformat(normalized)
            return not require_timezone
        parsed = dt.datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def comparable_time(value: str) -> dt.datetime:
    normalized = value.strip()
    if "T" not in normalized:
        parsed_date = dt.date.fromisoformat(normalized)
        return dt.datetime.combine(parsed_date, dt.time.min, tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_path", type=Path)
    args = parser.parse_args()
    case_dir = args.case_path if args.case_path.is_dir() else args.case_path.parent
    case_path = case_dir / "case.md"
    evidence_path = case_dir / "evidence.jsonl"
    errors: list[str] = []
    warnings: list[str] = []

    if not case_path.exists():
        errors.append(f"missing {case_path}")
        text = ""
        fields: dict[str, str] = {}
    else:
        text = case_path.read_text(encoding="utf-8")
        fields = parse_frontmatter(text)
        if not fields:
            errors.append("missing or malformed YAML frontmatter")

    missing = sorted(REQUIRED_KEYS - fields.keys())
    if missing:
        errors.append(f"missing frontmatter keys: {', '.join(missing)}")
    for field_name in sorted(NONEMPTY_CASE_FIELDS & fields.keys()):
        if not nonempty_string(fields[field_name]) or fields[field_name] == "null":
            errors.append(f"frontmatter {field_name} must be a non-empty string")
    if fields.get("trend_case_schema") not in {None, "shortform-trend-lifecycle-v1"}:
        errors.append("unsupported trend_case_schema")
    trend_id = fields.get("trend_id", "")
    trend_id_match = TREND_ID_RE.fullmatch(trend_id) if isinstance(trend_id, str) else None
    if trend_id and not trend_id_match:
        errors.append("trend_id must match YYYY-MM-DD_<kebab-case-slug>")
    if trend_id and case_dir.name != trend_id:
        errors.append(f"case directory name must equal trend_id: {trend_id}")
    if fields.get("discovered_on") and not valid_date(fields["discovered_on"]):
        errors.append("discovered_on must be an ISO 8601 date")
    if trend_id_match and fields.get("discovered_on") != trend_id_match.group(1):
        errors.append("trend_id date prefix must equal discovered_on")
    if fields.get("snapshot_at") and not valid_date_or_datetime(fields["snapshot_at"], require_timezone=True):
        errors.append("snapshot_at must be an ISO 8601 timestamp with timezone")
    if fields.get("confidence") and fields["confidence"] not in CONFIDENCE:
        errors.append(f"invalid confidence: {fields['confidence']}")
    stage = fields.get("current_stage")
    if stage and stage not in STAGES:
        errors.append(f"invalid current_stage: {stage}")
    window = fields.get("usable_window", "").split(" ", 1)[0]
    if window and window not in WINDOWS:
        errors.append(f"invalid usable_window: {fields.get('usable_window')}")
    milestone_times: dict[str, dt.datetime] = {}
    for field_name in MILESTONE_FIELDS:
        value = fields.get(field_name)
        if value in {None, "null"}:
            continue
        if not valid_date_or_datetime(value):
            errors.append(f"{field_name} must be an ISO 8601 date/timestamp or null")
            continue
        milestone_times[field_name] = comparable_time(value)
    onset = milestone_times.get("earliest_source_backed_at")
    breakout = milestone_times.get("first_breakout_at")
    copy_wave = milestone_times.get("copy_wave_onset_at")
    peak = milestone_times.get("peak_at")
    decay = milestone_times.get("decay_onset_at")
    for later_name, later_value in milestone_times.items():
        if onset and later_name != "earliest_source_backed_at" and onset > later_value:
            errors.append(f"earliest_source_backed_at cannot follow {later_name}")
    if breakout and peak and breakout > peak:
        errors.append("first_breakout_at cannot follow peak_at")
    if copy_wave and peak and copy_wave > peak:
        errors.append("copy_wave_onset_at cannot follow peak_at")
    if peak and decay and peak > decay:
        errors.append("peak_at cannot follow decay_onset_at")
    for section in REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"missing section: {section}")

    seen_ids: set[str] = set()
    evidence_count = 0
    if not evidence_path.exists():
        errors.append(f"missing {evidence_path}")
    else:
        for line_number, raw in enumerate(evidence_path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            evidence_count += 1
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"evidence line {line_number}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(item, dict):
                errors.append(f"evidence line {line_number}: JSON value must be an object")
                continue
            missing_evidence = sorted(EVIDENCE_KEYS - item.keys())
            if missing_evidence:
                errors.append(f"evidence line {line_number}: missing {', '.join(missing_evidence)}")
            for field_name in sorted(NONEMPTY_EVIDENCE_FIELDS & item.keys()):
                if not nonempty_string(item[field_name]):
                    errors.append(f"evidence line {line_number}: {field_name} must be a non-empty string")
            evidence_id = item.get("evidence_id")
            if isinstance(evidence_id, str):
                if evidence_id in seen_ids:
                    errors.append(f"evidence line {line_number}: duplicate evidence_id {evidence_id}")
                seen_ids.add(evidence_id)
            if not valid_url(item.get("url")):
                errors.append(f"evidence line {line_number}: invalid canonical url")
            published_at = item.get("published_at")
            if published_at is not None and not valid_date_or_datetime(published_at):
                errors.append(f"evidence line {line_number}: published_at must be an ISO 8601 date/timestamp or null")
            if published_at is None and not nonempty_string(item.get("notes")):
                errors.append(f"evidence line {line_number}: published_at null requires an explanatory note")
            if not valid_date_or_datetime(item.get("observed_at")):
                errors.append(f"evidence line {line_number}: observed_at must be an ISO 8601 date/timestamp")
            if item.get("role") not in ROLES:
                errors.append(f"evidence line {line_number}: invalid role {item.get('role')}")
            if item.get("format_match") not in MATCHES:
                errors.append(f"evidence line {line_number}: invalid format_match {item.get('format_match')}")
            credit_targets = item.get("credit_targets", [])
            if not isinstance(credit_targets, list) or not all(nonempty_string(target) for target in credit_targets):
                errors.append(f"evidence line {line_number}: credit_targets must be a list of non-empty strings")
            for metric in METRICS:
                value = item.get(metric)
                if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                    errors.append(f"evidence line {line_number}: {metric} must be a non-negative integer or null")

    if evidence_count == 0:
        warnings.append("evidence.jsonl is empty; case remains a scaffold")

    result = {
        "case": str(case_dir.resolve()),
        "valid": not errors,
        "evidence_count": evidence_count,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
