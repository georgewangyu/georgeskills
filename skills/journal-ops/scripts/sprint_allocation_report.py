#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from repo_paths import resolve_private_repo_root


PRIVATE_REPO_ROOT = resolve_private_repo_root()
SUMMARIES_ROOT = PRIVATE_REPO_ROOT / "journal" / "summaries"

DEEP_FOCUS_HOURS = 1.5
LIGHT_FOCUS_HOURS = 0.5


@dataclass
class Session:
    date: date
    title: str
    body: str
    intensity: str
    count: float
    domain: str
    source: str

    @property
    def focus_hours(self) -> float:
        if self.intensity == "unclassified":
            return 0.0
        per_session = DEEP_FOCUS_HOURS if self.intensity == "deep" else LIGHT_FOCUS_HOURS
        return self.count * per_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Infer sprint allocation from daily summaries and produce a retro-friendly report."
    )
    parser.add_argument("--start-date", required=True, help="Inclusive start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", required=True, help="Inclusive end date in YYYY-MM-DD format")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    parser.add_argument("--output", help="Optional file path to write the rendered report")
    parser.add_argument("--include-daily", action="store_true", help="Include daily breakdown in markdown output")
    return parser.parse_args()


def parse_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def daterange(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def summary_path_for(day: date) -> Path:
    return SUMMARIES_ROOT / day.strftime("%Y/%m/%Y-%m-%d_Summary.md")


def extract_section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def parse_float(raw: str) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def extract_metrics(text: str) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "energy": None,
        "mood": None,
        "focus": None,
        "productivity": None,
        "sleep_hours": None,
    }
    patterns = {
        "energy": [
            r"Energy(?: \(1[–-]5\))?\s*\|\s*`?([0-9.]+)",
            r"Energy:\s*`?([0-9.]+)",
        ],
        "mood": [
            r"Mood(?: \(1[–-]5\))?\s*\|\s*`?([0-9.]+)",
            r"Mood:\s*`?([0-9.]+)",
        ],
        "focus": [
            r"Focus(?: \(1[–-]5\))?\s*\|\s*`?([0-9.]+)",
            r"Focus:\s*`?([0-9.]+)",
        ],
        "productivity": [
            r"Productivity(?: \(1[–-]5\))?\s*\|\s*`?([0-9.]+)",
            r"Productivity:\s*`?([0-9.]+)",
        ],
        "sleep_hours": [
            r"`([0-9.]+)h`\s+sleep",
            r"sleep(?: landed at| was|:)?\s*`?([0-9.]+)\s*h`?",
        ],
    }
    for key, key_patterns in patterns.items():
        for pattern in key_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics[key] = parse_float(match.group(1))
                break
    return metrics


def normalize_whitespace(raw: str) -> str:
    return " ".join(raw.replace("—", " - ").replace("–", "-").split())


def extract_count(text: str) -> float:
    text = normalize_whitespace(text)
    range_match = re.search(
        r"`?([0-9]+(?:\.[0-9]+)?)`?\s*-\s*`?([0-9]+(?:\.[0-9]+)?)`?\s+deep sprints",
        text,
        re.I,
    )
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return round((low + high) / 2, 1)

    count_patterns = [
        r"\(x([0-9]+(?:\.[0-9]+)?)\)",
        r"\(×([0-9]+(?:\.[0-9]+)?)\)",
        r"`?([0-9]+(?:\.[0-9]+)?)`?\s+deep sprints\b",
        r"\b([0-9]+(?:\.[0-9]+)?)\s+sprints\b",
    ]
    for pattern in count_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return float(match.group(1))
    return 1.0


def split_tags(text: str) -> list[str]:
    return re.findall(r"\[([^\]]+)\]", text)


def infer_domain(title: str, body: str, tags: list[str]) -> str:
    title_haystack = normalize_whitespace(title).lower()
    body_haystack = normalize_whitespace(body).lower()
    tag_set = {tag.lower() for tag in tags}

    # Explicit structured tags are stronger evidence than incidental words in
    # the body. For example, a `[work]` block that mentions a video pipeline is
    # still day-job work, not Content.
    if tag_set.intersection({"job/interview/skills", "career"}):
        return "Career/Interview"
    if tag_set.intersection({"work", "day job"}):
        return "Day Job"
    if tag_set.intersection({"content", "publication", "video-workflow", "sports-radar"}):
        return "Content"
    if tag_set.intersection({"product", "personal project"}):
        return "Personal Project"
    if tag_set.intersection({"outreach", "business", "business/corp", "brand"}):
        return "Business/Admin"
    if tag_set.intersection({"workflow", "infra", "tooling", "repo", "research", "knowledge", "audio", "systems"}):
        return "Systems/Workflow"
    if tag_set.intersection({"personal", "travel", "health", "people"}):
        return "Personal"

    career_keywords = (
        "databricks",
        "interview",
        "resume",
        "application",
        "job hunt",
        "job-hunting",
        "leetcode",
        "coding interview",
        "phone screen",
        "skills",
        "career",
    )
    day_job_keywords = (
        "on-call",
        "presentation",
        "office",
        "amazon",
        "work block",
        "work presentation",
        "reverse shadow",
        "cr / review",
        "review chatter",
    )
    project_keywords = (
        "snackvoice",
        "ada",
        "xbot",
        "app build",
        "subscription",
        "updater",
        "website",
        "landing-page",
        "product-shape",
        "product lane",
        "build push",
        "qa pass",
        "bug-fix",
    )
    systems_keywords = (
        "workflow",
        "tooling",
        "infra",
        "infrastructure",
        "disk cleanup",
        "machine maintenance",
        "repo",
        "migration",
        "journal",
        "transcript",
        "export",
        "hydration",
        "capture",
        "maintenance",
        "cleanup",
    )
    content_keywords = (
        "content",
        "filming",
        "video",
        "tiktok",
        "x thread",
        "post drafting",
        "publishing",
        "linkedin",
        "youtube",
        "thread posting",
    )
    business_keywords = (
        "invoice",
        "pricing",
        "creator-offer",
        "outreach",
        "billing",
        "contract",
        "kumospace",
        "fonzi",
        "rootly",
        "questflow",
        "vibranium",
        "tax",
        "taxes",
        "email",
        "cross-posting",
    )
    personal_keywords = (
        "teresa",
        "family",
        "social",
        "tennis",
        "travel",
        "lunch",
        "ice cream",
        "basketball",
        "evening companion",
        "nba",
        "pizza",
        "meal",
    )

    keyword_groups = (
        ("Career/Interview", career_keywords),
        ("Day Job", day_job_keywords),
        ("Content", content_keywords),
        ("Business/Admin", business_keywords),
        ("Personal Project", project_keywords),
        ("Systems/Workflow", systems_keywords),
        ("Personal", personal_keywords),
    )
    scores: dict[str, int] = {}
    for domain, keywords in keyword_groups:
        title_score = sum(3 for keyword in keywords if keyword in title_haystack)
        body_score = sum(1 for keyword in keywords if keyword in body_haystack)
        scores[domain] = title_score + body_score
    best_domain, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score:
        return best_domain
    return "Systems/Workflow"


def infer_intensity(section: str | None, title: str, body: str, domain: str) -> str:
    if section == "deep":
        return "deep"
    if section == "light":
        return "light"

    haystack = normalize_whitespace(f"{title} {body}").lower()
    if "deep sprint" in haystack or "all-day app build" in haystack or "build push" in haystack:
        return "deep"
    if re.search(r"\bdeep(?:,|\)|:|\s)", haystack) or "multi-block" in haystack:
        return "deep"
    if any(token in haystack for token in ("travel", "social", "lunch", "ambient", "teresa", "tennis", "ice cream")):
        return "light"
    if re.search(r"\blight(?:,|\)|:|\s)", haystack):
        return "light"
    return "unclassified"


def parse_sprints_section(section_text: str, day: date) -> list[Session]:
    if not section_text:
        return []

    sessions: list[Session] = []
    current_section: str | None = None
    current_entry: dict[str, str] | None = None

    def flush_entry() -> None:
        nonlocal current_entry
        if not current_entry:
            return
        title = current_entry["title"].strip()
        body = current_entry["body"].strip()
        # Most summaries use `Label: details` on one bullet line. Treat the
        # short label as the title so a later incidental word (for example an
        # archived "interview" inside a content block) cannot dominate the
        # block's actual category.
        if ":" in title:
            label, inline_body = title.split(":", 1)
            if len(label) <= 120:
                title = label.strip()
                body = " ".join(part for part in (inline_body.strip(), body) if part)
        tags = split_tags(f"{title} {body}")
        domain = infer_domain(title, body, tags)
        intensity = infer_intensity(current_entry.get("section"), title, body, domain)
        count = extract_count(f"{title} {body}")
        sessions.append(
            Session(
                date=day,
                title=title,
                body=body,
                intensity=intensity,
                count=count,
                domain=domain,
                source="summary",
            )
        )
        current_entry = None

    lines = section_text.splitlines()
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### Deep Sprints"):
            flush_entry()
            current_section = "deep"
            continue
        if stripped.startswith("### Light Blocks"):
            flush_entry()
            current_section = "light"
            continue
        if stripped.startswith("**") and stripped.endswith("**") and "—" not in stripped and "-" not in stripped:
            continue

        entry_start = False
        title = ""
        if line.startswith("- "):
            entry_start = True
            title = line[2:].strip()
        elif stripped.startswith("**") and ("—" in stripped or "-" in stripped):
            entry_start = True
            title = stripped
        elif re.match(r"^[0-9]+[.)]\s+", line):
            entry_start = True
            title = re.sub(r"^[0-9]+[.)]\s+", "", line).strip()

        if entry_start:
            if title.endswith(":"):
                current_entry = None
                continue
            flush_entry()
            current_entry = {"title": title, "body": "", "section": current_section or ""}
            continue

        if current_entry:
            if current_entry["body"]:
                current_entry["body"] += " "
            current_entry["body"] += stripped.lstrip("- ").strip()

    flush_entry()
    return sessions


def extract_priority_bullets(section_text: str) -> list[str]:
    priorities = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            priorities.append(stripped[2:].strip())
    return priorities


def classify_priority(text: str) -> str | None:
    haystack = normalize_whitespace(text).lower()
    if any(token in haystack for token in ("databricks", "interview", "resume", "application", "job", "coding")):
        return "Career/Interview"
    if any(token in haystack for token in ("snackvoice", "ada", "xbot", "product", "subscription")):
        return "Personal Project"
    if any(token in haystack for token in ("video", "content", "tiktok", "x thread", "post")):
        return "Content"
    if any(token in haystack for token in ("workflow", "tooling", "repo", "migration", "cleanup")):
        return "Systems/Workflow"
    if any(token in haystack for token in ("invoice", "pricing", "billing", "offer", "contract", "tax")):
        return "Business/Admin"
    return None


def classify_primary_plan(section_text: str) -> str | None:
    match = re.search(r"### Primary Sprint\s*\n\s*-\s*(.+)", section_text)
    if not match:
        return None
    return classify_priority(match.group(1))


def load_day(day: date) -> dict:
    path = summary_path_for(day)
    if not path.exists():
        return {"date": day, "exists": False}

    text = path.read_text(encoding="utf-8")
    sprints_section = extract_section(text, "Sprints Today")
    priorities_section = extract_section(text, "Tomorrow Priorities")
    plan_section = extract_section(text, "Deep Sprint Plan")
    sessions = parse_sprints_section(sprints_section, day)
    metrics = extract_metrics(text)
    priorities = extract_priority_bullets(priorities_section)
    primary_plan = classify_primary_plan(plan_section)
    first_deep = next((session for session in sessions if session.intensity == "deep"), None)

    return {
        "date": day,
        "exists": True,
        "path": path,
        "metrics": metrics,
        "sessions": sessions,
        "priorities": priorities,
        "primary_plan": primary_plan,
        "primary_alignment": bool(primary_plan and first_deep and primary_plan == first_deep.domain),
    }


def average(values: list[float | None]) -> float | None:
    cleaned = [value for value in values if value is not None]
    if not cleaned:
        return None
    return round(sum(cleaned) / len(cleaned), 2)


def longest_streak(values: list[bool]) -> int:
    best = 0
    current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def build_report(days: list[dict]) -> dict:
    sessions = [session for day in days if day.get("exists") for session in day["sessions"]]
    deep_sessions = [session for session in sessions if session.intensity == "deep"]
    light_sessions = [session for session in sessions if session.intensity == "light"]
    unclassified_sessions = [session for session in sessions if session.intensity == "unclassified"]

    focus_hours_by_domain: dict[str, float] = defaultdict(float)
    count_by_domain: dict[str, float] = defaultdict(float)
    deep_count_by_domain: dict[str, float] = defaultdict(float)
    light_count_by_domain: dict[str, float] = defaultdict(float)
    for session in sessions:
        focus_hours_by_domain[session.domain] += session.focus_hours
        count_by_domain[session.domain] += session.count
        if session.intensity == "deep":
            deep_count_by_domain[session.domain] += session.count
        else:
            light_count_by_domain[session.domain] += session.count

    priorities_by_domain: dict[str, int] = Counter()
    daily_priority_domains: list[set[str]] = []
    for day in days:
        classified = {classify_priority(priority) for priority in day.get("priorities", [])}
        classified.discard(None)
        daily_priority_domains.append(classified)
        for domain in classified:
            priorities_by_domain[domain] += 1

    days_with_career_deep = 0
    days_with_career_activity = 0
    for day in days:
        if any(session.intensity == "deep" and session.domain == "Career/Interview" for session in day.get("sessions", [])):
            days_with_career_deep += 1
        if any(session.domain == "Career/Interview" for session in day.get("sessions", [])):
            days_with_career_activity += 1

    primary_alignment_values = [day["primary_alignment"] for day in days if day.get("primary_plan")]
    total_focus_hours = round(sum(focus_hours_by_domain.values()), 2)
    domain_percentages = {
        domain: round((hours / total_focus_hours) * 100, 1) if total_focus_hours else 0.0
        for domain, hours in sorted(focus_hours_by_domain.items())
    }
    total_activity_count = round(sum(count_by_domain.values()), 1)
    activity_percentages = {
        domain: round((count / total_activity_count) * 100, 1) if total_activity_count else 0.0
        for domain, count in sorted(count_by_domain.items())
    }

    daily_breakdown = []
    for day in days:
        session_summary = []
        for session in day.get("sessions", []):
            session_summary.append(
                {
                    "title": session.title,
                    "intensity": session.intensity,
                    "count": session.count,
                    "domain": session.domain,
                    "focus_hours": round(session.focus_hours, 2),
                }
            )
        daily_breakdown.append(
            {
                "date": day["date"].isoformat(),
                "metrics": day.get("metrics"),
                "sessions": session_summary,
                "priorities": day.get("priorities", []),
                "primary_plan": day.get("primary_plan"),
                "primary_alignment": day.get("primary_alignment"),
            }
        )

    report = {
        "window": {
            "start_date": days[0]["date"].isoformat(),
            "end_date": days[-1]["date"].isoformat(),
            "days_in_window": len(days),
            "days_tracked": sum(1 for day in days if day.get("exists")),
            "days_with_activity_records": sum(1 for day in days if day.get("sessions")),
        },
        "metrics": {
            "energy_avg": average([day.get("metrics", {}).get("energy") for day in days if day.get("exists")]),
            "mood_avg": average([day.get("metrics", {}).get("mood") for day in days if day.get("exists")]),
            "focus_avg": average([day.get("metrics", {}).get("focus") for day in days if day.get("exists")]),
            "productivity_avg": average([day.get("metrics", {}).get("productivity") for day in days if day.get("exists")]),
            "sleep_avg": average([day.get("metrics", {}).get("sleep_hours") for day in days if day.get("exists")]),
        },
        "allocation": {
            "total_focus_hours_est": total_focus_hours,
            "activity_record_count": total_activity_count,
            "deep_session_count_est": round(sum(session.count for session in deep_sessions), 1),
            "light_session_count_est": round(sum(session.count for session in light_sessions), 1),
            "unclassified_activity_count": round(sum(session.count for session in unclassified_sessions), 1),
            "activity_count_by_domain": {domain: round(value, 1) for domain, value in sorted(count_by_domain.items())},
            "activity_percentages": activity_percentages,
            "focus_hours_by_domain": {domain: round(hours, 2) for domain, hours in sorted(focus_hours_by_domain.items())},
            "deep_count_by_domain": {domain: round(value, 1) for domain, value in sorted(deep_count_by_domain.items())},
            "light_count_by_domain": {domain: round(value, 1) for domain, value in sorted(light_count_by_domain.items())},
            "domain_percentages": domain_percentages,
        },
        "execution": {
            "days_with_career_deep": days_with_career_deep,
            "days_without_career_deep": len(days) - days_with_career_deep,
            "days_with_career_activity": days_with_career_activity,
            "primary_plan_alignment_rate": (
                round(sum(primary_alignment_values) / len(primary_alignment_values) * 100, 1)
                if primary_alignment_values
                else None
            ),
            "primary_plan_days_measured": len(primary_alignment_values),
        },
        "carry_forward": {
            "priority_days_by_domain": dict(sorted(priorities_by_domain.items())),
            "career_priority_streak_days": longest_streak(
                ["Career/Interview" in domains for domains in daily_priority_domains]
            ),
            "project_priority_streak_days": longest_streak(
                ["Personal Project" in domains for domains in daily_priority_domains]
            ),
        },
        "daily_breakdown": daily_breakdown,
    }
    return report


def render_markdown(report: dict, include_daily: bool) -> str:
    allocation = report["allocation"]
    execution = report["execution"]
    carry = report["carry_forward"]
    metrics = report["metrics"]
    lines = [
        f"# Sprint Allocation Report",
        "",
        f"- **Window**: {report['window']['start_date']} to {report['window']['end_date']}",
        f"- **Days tracked**: {report['window']['days_tracked']} / {report['window']['days_in_window']}",
        f"- **Days with structured activity records**: {report['window']['days_with_activity_records']} / {report['window']['days_in_window']}",
        f"- **Activity records extracted**: {allocation['activity_record_count']}",
        f"- **Explicitly classified deep records**: {allocation['deep_session_count_est']}",
        f"- **Explicitly classified light records**: {allocation['light_session_count_est']}",
        f"- **Unclassified activity records**: {allocation['unclassified_activity_count']}",
        f"- **Focus hours estimated from explicit intensity only**: {allocation['total_focus_hours_est']}",
        "",
        "## Average Ratings",
        "",
        f"- **Energy**: {metrics['energy_avg']}",
        f"- **Mood**: {metrics['mood_avg']}",
        f"- **Focus**: {metrics['focus_avg']}",
        f"- **Productivity**: {metrics['productivity_avg']}",
        f"- **Sleep (hours)**: {metrics['sleep_avg']}",
        "",
        "## Activity Mix (Not Time Allocation)",
        "",
    ]
    for domain, count in allocation["activity_count_by_domain"].items():
        pct = allocation["activity_percentages"].get(domain, 0.0)
        deep = allocation["deep_count_by_domain"].get(domain, 0.0)
        light = allocation["light_count_by_domain"].get(domain, 0.0)
        lines.append(
            f"- **{domain}**: {count} records ({pct}%) | explicit deep {deep} | explicit light {light}"
        )

    lines.extend(
        [
            "",
            "## Execution Signals",
            "",
            f"- **Days with a career/interview activity record**: {execution['days_with_career_activity']}",
            f"- **Explicit career deep records**: {allocation['deep_count_by_domain'].get('Career/Interview', 0.0)}",
            f"- **Primary-plan first-block alignment**: {execution['primary_plan_alignment_rate']}% over {execution['primary_plan_days_measured']} measured days",
            "",
            "## Carry-Forward Pressure",
            "",
            f"- **Career/interview priority streak**: {carry['career_priority_streak_days']} days",
            f"- **Personal-project priority streak**: {carry['project_priority_streak_days']} days",
        ]
    )

    for domain, count in carry["priority_days_by_domain"].items():
        lines.append(f"- **Priority days mentioning {domain}**: {count}")

    if include_daily:
        lines.extend(["", "## Daily Breakdown", ""])
        for day in report["daily_breakdown"]:
            lines.append(f"### {day['date']}")
            lines.append(f"- **Primary plan**: {day['primary_plan']}")
            lines.append(f"- **Primary alignment**: {day['primary_alignment']}")
            for session in day["sessions"]:
                lines.append(
                    f"- `{session['intensity']}` {session['domain']} | x{session['count']} | {session['title']}"
                )
            if day["priorities"]:
                lines.append(f"- **Tomorrow priorities**: {'; '.join(day['priorities'])}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    start = parse_date(args.start_date)
    end = parse_date(args.end_date)
    days = [load_day(day) for day in daterange(start, end)]
    report = build_report(days)

    if args.json:
        rendered = json.dumps(report, indent=2)
    else:
        rendered = render_markdown(report, include_daily=args.include_daily)

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
