#!/usr/bin/env python3
"""Scan text artifacts for repeated workflows that may deserve skills."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst"}

CLUSTERS = {
    "transcript-processing": [
        r"\btranscript\b",
        r"\btranscribe\b",
        r"\bcaptions?\b",
        r"\bwhisper\b",
        r"\baudio\b",
    ],
    "journal-workflow": [
        r"\bdaily summary\b",
        r"\bjournal\b",
        r"\bconversation milestones?\b",
        r"\bmorning\b",
        r"\bcloseout\b",
    ],
    "pull-request-workflow": [
        r"\bpull request\b",
        r"\bPR\b",
        r"\breview comments?\b",
        r"\bCI\b",
        r"\bcommit\b",
    ],
    "agent-ops": [
        r"\bagents?\b",
        r"\bcodex\b",
        r"\bclaude code\b",
        r"\bcursor\b",
        r"\bskills?\b",
        r"\bworkflow\b",
    ],
    "research-scouting": [
        r"\bresearch\b",
        r"\btrend\b",
        r"\bscan\b",
        r"\bsignal\b",
        r"\bsource\b",
    ],
    "privacy-safety": [
        r"\bprivate\b",
        r"\bsecret\b",
        r"\btoken\b",
        r"\bPII\b",
        r"\bpublic-safe\b",
        r"\bsafety\b",
    ],
    "data-export": [
        r"\bexport\b",
        r"\bingest\b",
        r"\bimport\b",
        r"\bpipeline\b",
        r"\bartifact\b",
    ],
}

SUGGESTED_NAMES = {
    "agent-ops": "agent-ops",
    "data-export": "exports-ops",
    "journal-workflow": "journal-ops",
    "privacy-safety": "privacy-safety-ops",
    "pull-request-workflow": "pull-request-ops",
    "research-scouting": "research-scouting-ops",
    "transcript-processing": "transcript-processing-ops",
}

WORKFLOW_HINTS = [
    r"\brepeated\b",
    r"\bmanual\b",
    r"\bworkflow\b",
    r"\bblocker\b",
    r"\bfix(?:ed)?\b",
    r"\badded\b",
    r"\bpatched\b",
    r"\bcreated\b",
    r"\bconverted\b",
    r"\bvalidated\b",
    r"\bneeds? to\b",
    r"\bshould\b",
]


@dataclass(frozen=True)
class Evidence:
    path: Path
    line_number: int
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown digest of candidate workflows to promote into skills."
    )
    parser.add_argument(
        "--root",
        action="append",
        required=True,
        help="Directory or text file to scan. May be passed more than once.",
    )
    parser.add_argument(
        "--output",
        help="Optional Markdown output path. Defaults to stdout.",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        help="Only scan files modified within this many days.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=500,
        help="Maximum files to scan across all roots.",
    )
    parser.add_argument(
        "--max-evidence",
        type=int,
        default=5,
        help="Maximum evidence snippets per candidate.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=2,
        help="Minimum score required for a cluster to appear.",
    )
    return parser.parse_args()


def iter_text_files(roots: Iterable[Path], since_days: int | None, max_files: int) -> Iterable[Path]:
    cutoff = None
    if since_days is not None:
        cutoff = dt.datetime.now().timestamp() - since_days * 24 * 60 * 60

    seen: set[Path] = set()
    count = 0
    for root in roots:
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if count >= max_files:
                return
            if path in seen or not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if cutoff is not None and path.stat().st_mtime < cutoff:
                continue
            seen.add(path)
            count += 1
            yield path


def interesting_line(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 24:
        return False
    return any(re.search(pattern, stripped, re.IGNORECASE) for pattern in WORKFLOW_HINTS)


def matching_clusters(line: str) -> list[str]:
    matches = []
    for cluster, patterns in CLUSTERS.items():
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
            matches.append(cluster)
    return matches


def clean_excerpt(line: str, max_len: int = 220) -> str:
    line = re.sub(r"\s+", " ", line.strip())
    line = re.sub(r"^[-*]\s+", "", line)
    if len(line) <= max_len:
        return line
    return line[: max_len - 1].rstrip() + "..."


def collect_evidence(paths: Iterable[Path]) -> tuple[dict[str, list[Evidence]], Counter[str]]:
    evidence_by_cluster: dict[str, list[Evidence]] = defaultdict(list)
    score = Counter()
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            if not interesting_line(line):
                continue
            clusters = matching_clusters(line)
            for cluster in clusters:
                score[cluster] += 1
                evidence_by_cluster[cluster].append(
                    Evidence(path=path, line_number=index, text=clean_excerpt(line))
                )
    return evidence_by_cluster, score


def suggested_skill_name(cluster: str) -> str:
    return SUGGESTED_NAMES.get(cluster, f"{cluster}-ops")


def render_digest(
    evidence_by_cluster: dict[str, list[Evidence]],
    score: Counter[str],
    roots: list[Path],
    min_score: int,
    max_evidence: int,
) -> str:
    today = dt.date.today().isoformat()
    lines = [
        f"# Skill Candidate Digest - {today}",
        "",
        "## Scope",
        "",
    ]
    lines.extend(f"- `{root}`" for root in roots)
    lines.extend(
        [
            "",
            "## Ranked Candidates",
            "",
            "| Candidate | Score | Suggested skill | Why it may deserve a skill |",
            "|---|---:|---|---|",
        ]
    )

    ranked = [(cluster, count) for cluster, count in score.most_common() if count >= min_score]
    if not ranked:
        lines.append("| No candidates met the threshold. | 0 | - | Scan more sources or lower `--min-score`. |")
    for cluster, count in ranked:
        reason = (
            "Repeated artifact evidence suggests a stable workflow; review snippets before promoting."
        )
        lines.append(
            f"| `{cluster}` | {count} | `{suggested_skill_name(cluster)}` | {reason} |"
        )

    for cluster, _count in ranked:
        lines.extend(["", f"## {cluster}", ""])
        for item in evidence_by_cluster[cluster][:max_evidence]:
            lines.append(f"- `{item.path}:{item.line_number}` - {item.text}")
        lines.extend(
            [
                "",
                "Promotion checks:",
                "- Is there evidence from more than one artifact or session?",
                "- Is the trigger crisp enough for an agent to route correctly?",
                "- Are inputs and outputs stable?",
                "- Can private examples be replaced with reusable public-safe instructions?",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    roots = [Path(root).expanduser().resolve() for root in args.root]
    paths = list(iter_text_files(roots, args.since_days, args.max_files))
    evidence_by_cluster, score = collect_evidence(paths)
    digest = render_digest(evidence_by_cluster, score, roots, args.min_score, args.max_evidence)

    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(digest, encoding="utf-8")
        print(output)
    else:
        print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
