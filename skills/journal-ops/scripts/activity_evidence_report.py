#!/usr/bin/env python3
"""Local source coverage and reviewed activity bounds; never a time tracker.

Ambient headings are conversation-presence envelopes, not exclusive work.
Only separately reviewed, source-linked intervals enter activity-hour bounds.
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = timezone.utc
HEADING = re.compile(r"^## (\d{1,2}:\d{2}(?: [AP]M)?)\s*[-–]\s*(\d{1,2}:\d{2}(?: [AP]M)?)\s*$", re.M)


def days(start, end):
    while start <= end:
        yield start
        start += timedelta(days=1)


def local_instant(day, clock, zone):
    naive = datetime.combine(day, clock)
    options = set()
    for fold in (0, 1):
        value = naive.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if value.astimezone(zone).replace(tzinfo=None) == naive:
            options.add(value)
    # Reject ambiguous fall-back and nonexistent spring-forward local labels.
    return next(iter(options)) if len(options) == 1 else None


def clock(text):
    return datetime.strptime(text, "%I:%M %p" if "M" in text else "%H:%M").time()


def union_seconds(intervals):
    total = 0.0
    end = None
    for a, b in sorted(intervals):
        if b <= a:
            continue
        total += max(0, (b - max(a, end or a)).total_seconds())
        end = max(b, end or b)
    return total


def ambient_day(path, day, zone, rules):
    result = {"source": str(path), "exists": path.is_file(), "segments": 0,
              "zero_minute_segments": 0, "ambiguous_or_boundary_segments": 0,
              "envelope_seconds": 0, "topics": {}, "first_label": None, "last_label": None}
    if not path.is_file():
        return result
    text = path.read_text(encoding="utf-8")
    headings = list(HEADING.finditer(text))
    intervals = []
    topics = defaultdict(list)
    for i, match in enumerate(headings):
        result["segments"] += 1
        start_clock, end_clock = clock(match[1]), clock(match[2])
        if result["first_label"] is None:
            result["first_label"] = match[1]
        result["last_label"] = match[2]
        line = text.count("\n", 0, match.start()) + 1
        body = text[match.end():headings[i + 1].start() if i + 1 < len(headings) else len(text)]
        for category, patterns in rules.items():
            if any(re.search(pattern, body, re.I) for pattern in patterns):
                topics[category].append(line)
        if end_clock < start_clock:
            result["ambiguous_or_boundary_segments"] += 1
            continue  # No date rollover guessed from minute-only headings.
        a, b = local_instant(day, start_clock, zone), local_instant(day, end_clock, zone)
        if a is None or b is None:
            result["ambiguous_or_boundary_segments"] += 1
        elif a == b:
            result["zero_minute_segments"] += 1
        else:
            intervals.append((a, b))
    result["envelope_seconds"] = union_seconds(intervals)
    result["topics"] = dict(topics)
    return result


def reviewed_intervals(path, categories, zone=None):
    if path is None or not path.is_file():
        return []
    result = json.loads(path.read_text())
    for item in result:
        a, b = datetime.fromisoformat(item["start"]), datetime.fromisoformat(item["end"])
        if a.utcoffset() is None or b.utcoffset() is None:
            raise ValueError("Reviewed timestamps require explicit offsets")
        if zone is not None and any(value.utcoffset() != value.astimezone(zone).utcoffset()
                                    for value in (a, b)):
            raise ValueError("Reviewed timestamp offset conflicts with policy timezone; convert to that timezone")
        a, b = a.astimezone(UTC), b.astimezone(UTC)
        if b <= a or item["category"] not in categories:
            raise ValueError("Invalid reviewed interval or category")
        if item["basis"] not in {"observed_active", "inferred_active", "passive_media", "background_worker", "host_gap"}:
            raise ValueError("Unknown evidence basis")
        source = Path(item["source"])
        if not source.is_file() or not item.get("rationale") or not item.get("host_scope"):
            raise ValueError("Reviewed evidence needs existing source, rationale and host scope")
        if not isinstance(item.get("line"), int) or item["line"] < 1:
            raise ValueError("Reviewed evidence needs source line")
        uncertainty = item.get("boundary_uncertainty_seconds", 0)
        if not isinstance(uncertainty, (int, float)) or not 0 <= uncertainty <= 3600:
            raise ValueError("Boundary uncertainty must be 0..3600 seconds")
        delta = timedelta(seconds=uncertainty)
        item["a"], item["b"] = a - delta, b + delta
        item["core_a"], item["core_b"] = min(a + delta, b), max(b - delta, a)
    return result


def activity_bounds(intervals, start, end, categories):
    """Partition UTC once. Conflicting categories and explicit host gaps stay unknown.

    Bounds describe only supported intervals, never a whole-day upper limit.
    Inferred active intervals have zero lower bound. Media/workers add no time.
    """
    relevant = [i for i in intervals if i["a"] < end and i["b"] > start]
    points = sorted({start, end, *(max(start, i["a"]) for i in relevant),
                     *(min(end, i["b"]) for i in relevant),
                     *(max(start, min(end, i.get("core_a", i["a"]))) for i in relevant),
                     *(max(start, min(end, i.get("core_b", i["b"]))) for i in relevant)})
    totals = {c: {"lower_seconds": 0.0, "upper_seconds": 0.0} for c in categories}
    conflicts = 0.0
    for a, b in zip(points, points[1:]):
        active = [i for i in relevant if i["a"] <= a and i["b"] >= b]
        candidates = [i for i in active if i["basis"] in {"observed_active", "inferred_active"}]
        labels = {i["category"] for i in candidates}
        seconds = (b - a).total_seconds()
        if len(labels) > 1 or (labels and any(i["basis"] == "host_gap" for i in active)):
            conflicts += seconds
        elif len(labels) == 1:
            category = next(iter(labels))
            totals[category]["upper_seconds"] += seconds
            if any(i["basis"] == "observed_active" and i.get("core_a", i["a"]) <= a
                   and i.get("core_b", i["b"]) >= b for i in candidates):
                totals[category]["lower_seconds"] += seconds
    assigned = sum(v["upper_seconds"] for v in totals.values())
    elapsed = (end - start).total_seconds()
    return {"categories": totals, "elapsed_seconds": elapsed,
            "unassigned_wallclock_seconds": elapsed - assigned, "conflict_seconds": conflicts,
            "unassigned_wallclock_fraction": (elapsed - assigned) / elapsed}


def screen_metadata(root, day):
    path = root / day.strftime("%Y/%m/%d/events.jsonl")
    result = {"source": str(path), "exists": path.is_file(), "samples": 0,
              "first": None, "last": None, "invalid": 0}
    if path.is_file():
        for line in path.read_text().splitlines():
            try:
                stamp = datetime.fromisoformat(json.loads(line)["timestamp"])
                if stamp.utcoffset() is None:
                    raise ValueError("Missing offset")
                stamp = stamp.astimezone(UTC).isoformat()
                result["samples"] += 1
                result["first"] = min(stamp, result["first"] or stamp)
                result["last"] = max(stamp, result["last"] or stamp)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                result["invalid"] += 1
    # Samples cannot establish continuous active time or a work category.
    return result


def summary_activity_lines(text):
    """Exclude plans, source digests and carry-forward queues from presence counts."""
    selected = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            selected = line[3:].strip() in {"Sprints Today", "Today at a Glance", "What Actually Happened", "Daily Log", "Day Narrative"}
        elif selected:
            yield n, line


def build_report(policy, start, end):
    if end < start:
        raise ValueError("End date precedes start date")
    zone = ZoneInfo(policy["timezone"])
    categories = list(policy["topic_rules"])
    reviewed = reviewed_intervals(Path(policy["reviewed_intervals"]).expanduser()
                                  if policy.get("reviewed_intervals") else None, categories, zone)
    ambient_root = Path(policy["ambient_root"]).expanduser()
    summaries = Path(policy["summaries_root"]).expanduser()
    screen_root = Path(policy["screen_archive_root"]).expanduser()
    rows = []
    for day in days(start, end):
        a = datetime.combine(day, time(), zone).astimezone(UTC)
        b = datetime.combine(day + timedelta(days=1), time(), zone).astimezone(UTC)
        summary = summaries / day.strftime("%Y/%m/%Y-%m-%d_Summary.md")
        text = summary.read_text() if summary.is_file() else ""
        rows.append({"date": day.isoformat(), "summary_source": str(summary),
                     "summary_exists": summary.is_file(),
                     "summary_topics": {c: [n for n, line in summary_activity_lines(text)
                                             if any(re.search(p, line, re.I) for p in patterns)]
                                        for c, patterns in policy["topic_rules"].items()},
                     "ambient": ambient_day(ambient_root / f"{day}.md", day, zone, policy["topic_rules"]),
                     "screen": screen_metadata(screen_root, day),
                     "activity": activity_bounds(reviewed, a, b, categories)})
    months = {}
    for row in rows:
        month = row["date"][:7]
        m = months.setdefault(month, {"calendar_days_in_month": calendar.monthrange(int(month[:4]), int(month[5:]))[1],
                                     "days_in_window": 0, "summary_days": 0, "ambient_days": 0,
                                     "screen_days": 0, "ambient_envelope_seconds": 0})
        m["days_in_window"] += 1
        m["summary_days"] += int(row["summary_exists"])
        m["ambient_days"] += int(row["ambient"]["exists"])
        m["screen_days"] += int(row["screen"]["exists"])
        m["ambient_envelope_seconds"] += row["ambient"]["envelope_seconds"]
    a = datetime.combine(start, time(), zone).astimezone(UTC)
    b = datetime.combine(end + timedelta(days=1), time(), zone).astimezone(UTC)
    evidence = [{k: v for k, v in i.items() if k not in {"a", "b", "core_a", "core_b"}}
                for i in reviewed if i["a"] < b and i["b"] > a]
    topics = {c: {"summary_presence_days": sum(bool(r["summary_topics"][c]) for r in rows),
                  "ambient_presence_days": sum(bool(r["ambient"]["topics"].get(c)) for r in rows)}
              for c in categories}
    signals = []
    threshold = policy.get("recurrence_review_min_days", 2)
    for category, values in topics.items():
        if category.startswith("admin_") and values["summary_presence_days"] >= threshold:
            signals.append({"kind": "recurrence_review", "category": category,
                            "summary_presence_days": values["summary_presence_days"],
                            "interpretation": "Review whether these are new actions, external waits, or avoidable reopenings; not a time or budget violation.",
                            "sources": [{"path": r["summary_source"], "lines": r["summary_topics"][category]}
                                        for r in rows if r["summary_topics"][category]]})
    return {"schema": "activity-evidence-v1", "start": str(start), "end": str(end),
            "timezone": policy["timezone"], "months": months, "days": rows,
            "activity": activity_bounds(reviewed, a, b, categories), "topic_presence": topics,
            "reviewed_evidence": evidence, "budget_status": "no_agreed_numeric_budgets",
            "signals": signals,
            "priority_source": policy.get("priority_source"),
            "source_status": {"ambient_root_exists": ambient_root.is_dir(),
                              "screen_archive_root_exists": screen_root.is_dir(),
                              "screen_config_path_mismatch": bool(policy.get("configured_screen_archive_root") and
                                  policy["configured_screen_archive_root"] != str(screen_root)),
                              "scope": "Local sources only; no claim of all-device coverage or live collector health"},
            "limitations": ["Unassigned wallclock includes sleep, offline time and work-laptop blind spots; it is not discretionary capacity.",
                            "Ambient envelope union uses file dates and minute labels; zero-minute, DST-ambiguous and cross-midnight blocks add no duration.",
                            "Ambient topics may be passive media, other speakers or multitasking; topics overlap and never create activity hours.",
                            "Observed active intervals are retrospective source-supported estimates, not stopwatch measurements.",
                            "Background worker runtime and screen samples do not establish human active time.",
                            "Daily outputs may be partial; rerun after closeout. Missing sources never mean zero work."]}


def markdown(report):
    lines = ["---", "doc_schema: doc-frontmatter-v1", f"doc_id: activity-evidence/{report['start']}/{report['end']}",
             "doc_type: report", "doc_status: derived", "title: Activity evidence",
             "description: Source coverage and reviewed activity bounds, not a complete time allocation.",
             "doc_tags: [domain:journal, type:derived-report]", "memory_eligible: false", "memory_priority: low", "---", "",
             f"# Activity evidence: {report['start']} to {report['end']}", "",
             "Supported activity bounds below cover reviewed intervals only. They are not total hours or time shares.", "",
             "| Category | Supported hours (lower–upper) | Summary presence days | Ambient topic days |",
             "| --- | ---: | ---: | ---: |"]
    for c, values in report["activity"]["categories"].items():
        topics = report["topic_presence"][c]
        bounds = (f"{values['lower_seconds']/3600:.2f}–{values['upper_seconds']/3600:.2f}"
                  if values['upper_seconds'] else "unquantified")
        lines.append(f"| {c} | {bounds} | {topics['summary_presence_days']} | {topics['ambient_presence_days']} |")
    lines += ["", f"Unassigned wallclock: {report['activity']['unassigned_wallclock_seconds']/3600:.2f}h "
              f"({report['activity']['unassigned_wallclock_fraction']:.1%}); includes sleep and all unobserved activity.", "",
              "| Month | Days in window | Summaries | Ambient files | Screen event days |", "| --- | ---: | ---: | ---: | ---: |"]
    for month, values in report["months"].items():
        lines.append(f"| {month} | {values['days_in_window']} | {values['summary_days']} | {values['ambient_days']} | {values['screen_days']} |")
    lines += ["", "## Reviewed evidence", ""]
    for i in report["reviewed_evidence"]:
        lines.append(f"- {i['start']}–{i['end']}: {i['category']}, {i['basis']}. "
                     f"{i['rationale']} [Source]({i['source']}:{i['line']}).")
    lines += ["", "## Review signals", ""]
    for signal in report["signals"]:
        lines.append(f"- {signal['category']}: present on {signal['summary_presence_days']} summary days. {signal['interpretation']}")
    lines += ["", "## Limits", "", *[f"- {s}" for s in report["limitations"]], "",
              "No agreed numeric budgets loaded. No automatic calendar, priority or recording changes.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--date", type=date.fromisoformat, help="Refresh daily, trailing seven-day and fourteen-day rollups")
    parser.add_argument("--output-prefix", type=Path)
    args = parser.parse_args(argv)
    policy = json.loads(args.policy.read_text())
    if args.date:
        root = Path(policy["derived_root"]).expanduser()
        windows = [(args.date, args.date, root / "daily" / str(args.date)),
                   (args.date - timedelta(days=6), args.date, root / "weekly" / str(args.date)),
                   (args.date - timedelta(days=13), args.date, root / "sprint" / str(args.date))]
    elif args.start_date and args.end_date and args.output_prefix:
        windows = [(args.start_date, args.end_date, args.output_prefix)]
    else:
        parser.error("Use --date or --start-date/--end-date/--output-prefix")
    for start, end, prefix in windows:
        report = build_report(policy, start, end)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        for suffix, content in ((".json", json.dumps(report, indent=2) + "\n"), (".md", markdown(report))):
            target = prefix.with_suffix(suffix)
            descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=".activity-")
            try:
                with os.fdopen(descriptor, "w") as stream:
                    stream.write(content)
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
        print(f"Activity evidence: {prefix}.json (derived locally; no model calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
