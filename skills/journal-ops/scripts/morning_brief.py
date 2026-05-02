#!/usr/bin/env python3
"""
Morning brief for start-of-day chat.

This is meant to be the script behind a cue like "morning" or
"this is the start of my day".
"""

from __future__ import annotations

import argparse
import csv
from html.parser import HTMLParser
import json
import os
import re
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
PAUL_GRAHAM_ESSAYS_URL = "https://paulgraham.com/articles.html"
PAUL_GRAHAM_BASE = "https://paulgraham.com/"
READING_CACHE_DIR = ROOT / ".cache" / "morning-radar"
PAUL_GRAHAM_CACHE = READING_CACHE_DIR / "paulgraham_essays.json"


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
        for item in items[:5]:
            likes = item.get("likes", 0)
            replies = item.get("replies", 0)
            text = shorten(item.get("text", ""), 160)
            tweet_id = item.get("id", "")
            suffix = f" ({likes} likes, {replies} replies"
            if tweet_id:
                suffix += f", id {tweet_id}"
            suffix += ")"
            print(f"  - {text}{suffix}")


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


def product_hunt_url_for(day_text: str) -> str:
    year, month, day = [int(part) for part in day_text.split("-")]
    return f"{PRODUCT_HUNT_BASE}/leaderboard/daily/{year}/{month}/{day}"


def print_product_hunt_scan(day_text: str, limit: int = 5) -> None:
    print("\n--- Product Hunt Radar ---")
    url = product_hunt_url_for(day_text)
    try:
        text = fetch_text(url)
    except Exception as exc:  # noqa: BLE001 - this is a best-effort morning signal.
        print(f"- Product Hunt unavailable: {shorten(str(exc), 180)}")
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    products: list[tuple[str, str, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if not match:
            continue
        rank = int(match.group(1))
        if rank > limit:
            continue
        name = match.group(2)
        tagline = ""
        metrics: list[str] = []
        for candidate in lines[index + 1 : index + 8]:
            if re.match(r"^\d+\.\s+", candidate):
                break
            if not tagline and not candidate.startswith("Image:") and not candidate.startswith("Promoted"):
                tagline = candidate
            if re.fullmatch(r"[\d,]+", candidate):
                metrics.append(candidate)
        metric_text = ""
        if len(metrics) >= 2:
            metric_text = f"{metrics[-1]} votes, {metrics[-2]} comments"
        elif metrics:
            metric_text = f"{metrics[-1]} votes/comments"
        products.append((name, tagline, metric_text))

    if not products:
        print(f"- No ranked products parsed from {url}")
        return

    print(f"- Source: {url}")
    for name, tagline, metric_text in products:
        detail = f" — {tagline}" if tagline else ""
        metrics = f" ({metric_text})" if metric_text else ""
        print(f"  - {name}{detail}{metrics}")


def normalize_paul_graham_href(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return PAUL_GRAHAM_BASE + href.lstrip("/")


def load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_paul_graham_essays(limit: int = 8) -> list[dict[str, str]]:
    html = fetch_html(PAUL_GRAHAM_ESSAYS_URL)
    parser = LinkExtractor()
    parser.feed(html)

    essays: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in parser.links:
        href = link["href"]
        title = link["title"]
        if not href.endswith(".html"):
            continue
        if title.lower() in {"essays"}:
            continue
        url = normalize_paul_graham_href(href)
        if url in seen:
            continue
        seen.add(url)
        essays.append({"title": title, "url": url})

    # The page starts with three recommendation links before the newest-first
    # essay list. Drop that intro block when it is present.
    recommendation_titles = {"How to Do Great Work", "Having Kids", "How to Lose Time and Money"}
    if len(essays) > 3 and {item["title"] for item in essays[:3]} == recommendation_titles:
        essays = essays[3:]

    return essays[:limit]


def print_paul_graham_scan(day_text: str, limit: int, update_cache: bool) -> None:
    print("\n--- Paul Graham Reading Radar ---")
    try:
        essays = fetch_paul_graham_essays(limit=limit)
    except Exception as exc:  # noqa: BLE001 - reading radar should not break morning prep.
        print(f"- Paul Graham essays unavailable: {shorten(str(exc), 180)}")
        return

    if not essays:
        print("- No essays parsed from Paul Graham essays page.")
        return

    previous = load_json_file(PAUL_GRAHAM_CACHE)
    previous_urls = {item.get("url") for item in previous.get("essays", []) if item.get("url")}
    current_urls = {item["url"] for item in essays}
    new_items = [item for item in essays if item["url"] not in previous_urls]

    print(f"- Source: {PAUL_GRAHAM_ESSAYS_URL}")
    if previous_urls:
        if new_items:
            print(f"- New since last cached check: {len(new_items)}")
            for item in new_items[:3]:
                print(f"  - {item['title']} — {item['url']}")
        elif previous_urls == current_urls:
            print("- No change in the top essay set since the last cached check.")
        else:
            print("- Top essay set changed since the last cached check.")
    else:
        print("- No previous cache found; seeding from the current top essay list.")

    print("- Current top essays:")
    for item in essays[:5]:
        print(f"  - {item['title']} — {item['url']}")

    print("- Reading note: pick one essay only if it sharpens today's build, writing, or founder judgment. Otherwise this becomes noble procrastination in vintage HTML clothing.")

    if update_cache:
        write_json_file(
            PAUL_GRAHAM_CACHE,
            {
                "checked_date": day_text,
                "source": PAUL_GRAHAM_ESSAYS_URL,
                "essays": essays,
            },
        )


def print_yc_scan(limit: int = 5) -> None:
    print("\n--- YC / Launch HN Radar ---")
    try:
        text = fetch_text(HN_LAUNCHES_URL)
    except Exception as exc:  # noqa: BLE001 - this is a best-effort morning signal.
        print(f"- Launch HN unavailable: {shorten(str(exc), 180)}")
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    launches: list[tuple[str, str]] = []
    for index, line in enumerate(lines):
        if not line.startswith("Launch HN:"):
            continue
        meta = ""
        for candidate in lines[index + 1 : index + 5]:
            if " points by " in candidate or " point by " in candidate:
                meta = candidate
                break
        launches.append((line, meta))
        if len(launches) >= limit:
            break

    if not launches:
        print("- No Launch HN items parsed.")
        return

    print(f"- Source: {HN_LAUNCHES_URL}")
    for title, meta in launches:
        suffix = f" ({shorten(meta, 90)})" if meta else ""
        print(f"  - {title}{suffix}")


def print_market_radar(day_text: str, x_count: int) -> None:
    print_x_scan(x_count)
    print_github_trends()
    print_yc_scan()
    print_product_hunt_scan(day_text)


def print_reading_radar(day_text: str, paul_graham_limit: int, update_cache: bool) -> None:
    print_paul_graham_scan(day_text, limit=paul_graham_limit, update_cache=update_cache)


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
        "--skip-reading-radar",
        action="store_true",
        help="Skip morning reading scans such as Paul Graham essays.",
    )
    parser.add_argument(
        "--paul-graham-limit",
        type=int,
        default=8,
        help="Number of Paul Graham essays to inspect from the top of the essays page.",
    )
    parser.add_argument(
        "--no-update-reading-cache",
        action="store_true",
        help="Do not update local reading-radar cache after checking reading sources.",
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

    if not args.skip_market_radar:
        print_market_radar(day_text, args.market_radar_x_count)
    if not args.skip_reading_radar:
        print_reading_radar(
            day_text,
            paul_graham_limit=args.paul_graham_limit,
            update_cache=not args.no_update_reading_cache,
        )
    print_morning_publishing_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
