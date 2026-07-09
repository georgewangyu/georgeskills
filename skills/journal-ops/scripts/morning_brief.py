#!/usr/bin/env python3
"""
Morning brief for start-of-day chat.

This is meant to be the script behind a cue like "morning" or
"this is the start of my day".
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import csv
from html.parser import HTMLParser
from io import StringIO
import json
import os
import subprocess
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

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
WORKSPACE_ROOT = ROOT.parent
XBOT_CLI = WORKSPACE_ROOT / "xbot" / "src" / "cli.js"
X_ENV = ROOT / ".tokens" / "x-twitter.env"
PRODUCT_HUNT_BASE = "https://www.producthunt.com"
HN_LAUNCHES_URL = "https://news.ycombinator.com/launches"
MARKET_RADAR_SCAN_TEMPLATE_ENV = "JOURNAL_OPS_MARKET_RADAR_SCAN_TEMPLATE"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        self._active_href = attr_map.get("href")
        self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._active_href is not None:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._active_href is None:
            return
        title = " ".join("".join(self._active_text).split())
        if title:
            self.links.append({"title": title, "href": self._active_href})
        self._active_href = None
        self._active_text = []


def absolute_hn_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"https://news.ycombinator.com/{href.lstrip('/')}"


def summary_path_for(day_text: str) -> Path:
    year, month, _ = day_text.split("-")
    return ROOT / "journal" / "summaries" / year / month / f"{day_text}_Summary.md"


def market_radar_scan_path_for(day_text: str) -> Path:
    year, month, _ = day_text.split("-")
    template = os.environ.get(MARKET_RADAR_SCAN_TEMPLATE_ENV)
    if template:
        rendered = (
            template.replace("YYYY-MM-DD", day_text)
            .replace("YYYY", year)
            .replace("MM", month)
        )
        return Path(rendered).expanduser()
    return ROOT / "journal" / "external-signal-scans" / year / month / f"{day_text}-market-radar.md"


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


def shorten(text: str, limit: int = 140) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def fetch_html(url: str, timeout: int = 12) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 morning-brief/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        proc = subprocess.run(
            [
                "curl",
                "-L",
                "--max-time",
                str(timeout),
                "-A",
                "Mozilla/5.0 morning-brief/1.0",
                "-H",
                "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-s",
                url,
            ],
            text=True,
            capture_output=True,
            timeout=timeout + 2,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout or "fetch failed")
        html = proc.stdout
    if "Just a moment..." in html and "challenge-platform" in html:
        raise RuntimeError("blocked by browser challenge")
    return html


def fetch_text(url: str, timeout: int = 12) -> str:
    html = fetch_html(url, timeout=timeout)
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()


def print_x_scan(count: int) -> None:
    print("\n--- X Radar ---")
    if not XBOT_CLI.exists():
        print("- xbot CLI not found; skipping X scan.")
        return

    env = os.environ.copy()
    env.update(load_env_file(X_ENV))

    for label, command in [("For You", "home"), ("Following", "latest")]:
        proc = subprocess.run(
            ["node", str(XBOT_CLI), command, "--count", str(count)],
            cwd=WORKSPACE_ROOT,
            text=True,
            capture_output=True,
            env=env,
            timeout=18,
        )
        if proc.returncode != 0:
            error = shorten(proc.stderr or proc.stdout or "unknown error", 180)
            print(f"- {label}: unavailable ({error})")
            continue

        try:
            items = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(f"- {label}: returned non-JSON output")
            continue

        if not items:
            print(f"- {label}: no items returned")
            continue

        print(f"- {label}:")
        for item in items[:count]:
            author = item.get("author") or ""
            author_name = item.get("authorName") or author
            followers = item.get("authorFollowers")
            following = item.get("authorFollowing")
            likes = item.get("likes", 0)
            retweets = item.get("retweets", 0)
            replies = item.get("replies", 0)
            views = item.get("views", 0)
            text = shorten(item.get("text", ""), 160)
            url = item.get("url") or ""
            handle = f"@{author}" if author else "unknown author"
            display = f"{author_name} ({handle})" if author_name and author_name != author else handle
            account = "followers unavailable"
            if followers is not None:
                account = f"{followers} followers"
                if following is not None:
                    account += f", {following} following"
            metrics = f"{likes} likes, {retweets} reposts, {replies} replies"
            if views:
                metrics += f", {views} views"
            link = f" — {url}" if url else ""
            print(f"  - {display}: {text} (account: {account}; {metrics}){link}")


def print_github_trends():
    if not GITHUB_TRENDS_SCRIPT.exists():
        return

    print("\n--- GitHub Trending ---")
    for period in ["daily", "weekly"]:
        proc = subprocess.run(
            ["python3", str(GITHUB_TRENDS_SCRIPT), "--since", period, "--limit", "5"],
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


def product_hunt_url_for(day_text: str) -> str:
    year, month, day = [int(part) for part in day_text.split("-")]
    return f"{PRODUCT_HUNT_BASE}/leaderboard/daily/{year}/{month}/{day}"


def print_product_hunt_scan(day_text: str, limit: int = 5) -> None:
    print("\n--- Product Hunt Radar ---")
    today_url = PRODUCT_HUNT_BASE
    archive_url = product_hunt_url_for(day_text)
    print("- Product Hunt is intentionally delegated to web/browser lookup; terminal fetches are consistently challenge-prone.")
    print(f"- Check today's launches: {today_url}")
    print(f"- Check daily archive when available: {archive_url}")
    print("- Summarize a few launch links with taglines, traction, and one practical wedge/positioning takeaway.")


def print_yc_scan(limit: int = 5) -> None:
    print("\n--- YC / Launch HN Radar ---")
    try:
        html = fetch_html(HN_LAUNCHES_URL)
    except Exception as exc:  # noqa: BLE001 - this is a best-effort morning signal.
        print(f"- Launch HN unavailable: {shorten(str(exc), 180)}")
        return

    parser = LinkExtractor()
    parser.feed(html)
    launches: list[dict[str, str]] = []
    for link in parser.links:
        title = link["title"]
        if not title.startswith("Launch HN:"):
            continue
        launches.append({"title": title, "url": absolute_hn_url(link["href"])})
        if len(launches) >= limit:
            break

    if not launches:
        print("- No Launch HN items parsed.")
        return

    print(f"- Source: {HN_LAUNCHES_URL}")
    for launch in launches:
        print(f"  - {launch['title']} — {launch['url']}")


def print_market_radar(day_text: str, x_count: int) -> None:
    print_x_scan(x_count)
    print_github_trends()
    print_yc_scan()
    print_product_hunt_scan(day_text)


def write_market_radar_scan(day_text: str, market_output: str, path: Path | None = None) -> Path:
    scan_path = path or market_radar_scan_path_for(day_text)
    scan_path.parent.mkdir(parents=True, exist_ok=True)
    scan_path.write_text(
        "\n".join(
            [
                f"# Market Radar Scan - {day_text}",
                "",
                "Source: generated by `morning_brief.py` from terminal-accessible morning radar sources.",
                "",
                "Boundary:",
                "- Expand this file with browser/Product Hunt details and final synthesis when the morning routine runs in a full agent thread.",
                "- Keep the daily journal to selected actions, decisions, blockers, durable lessons, and a link back to this scan.",
                "",
                market_output.rstrip(),
                "",
                "## What This Means",
                "",
                "- TODO: Add the repeated pattern, strongest planning implication, and one concrete action or proof object.",
                "",
                "## Signal Routing / Recommendations",
                "",
                "- TODO: Route into Ignition Event Candidates, Skill / Automation Candidates, Repos / Tweets To Study, Content Ideas, and Personal Project Candidates.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return scan_path


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
    parser.add_argument(
        "--skip-market-radar",
        action="store_true",
        help="Skip X, GitHub, YC/Launch HN, and Product Hunt morning scans.",
    )
    parser.add_argument(
        "--market-radar-x-count",
        type=int,
        default=8,
        help="Number of X items to request from each timeline during the market radar scan.",
    )
    parser.add_argument(
        "--write-market-radar-scan",
        action="store_true",
        help="Write terminal-accessible market radar output to the configured external-signal scan path.",
    )
    parser.add_argument(
        "--market-radar-scan-path",
        help="Override the market radar scan output path.",
    )
    parser.add_argument("--skip-reading-radar", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--paul-graham-limit", type=int, default=8, help=argparse.SUPPRESS)
    parser.add_argument("--no-update-reading-cache", action="store_true", help=argparse.SUPPRESS)
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

    if not args.skip_market_radar:
        if args.write_market_radar_scan:
            buffer = StringIO()
            with redirect_stdout(buffer):
                print_market_radar(day_text, args.market_radar_x_count)
            market_output = buffer.getvalue()
            print(market_output, end="")
            override_path = Path(args.market_radar_scan_path).expanduser() if args.market_radar_scan_path else None
            scan_path = write_market_radar_scan(day_text, market_output, override_path)
            print(f"\n- Market radar scan written: {scan_path}")
        else:
            print_market_radar(day_text, args.market_radar_x_count)
    print_morning_publishing_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
