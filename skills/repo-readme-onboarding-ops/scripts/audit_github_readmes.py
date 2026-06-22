#!/usr/bin/env python3
"""Audit GitHub repository README and About metadata quality.

This script uses the GitHub CLI so authentication and host selection remain in
the user's existing `gh` configuration.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


README_FIELDS = [
    "name",
    "description",
    "isPrivate",
    "url",
    "homepageUrl",
    "repositoryTopics",
    "primaryLanguage",
    "pushedAt",
]


@dataclass
class RepoAudit:
    name: str
    visibility: str
    url: str
    description: str
    homepage: str
    topics: list[str]
    primary_language: str
    pushed_at: str
    readme_exists: bool
    readme_words: int
    first_heading: str
    first_nonempty: str
    score: int
    severity: str
    findings: list[str]
    recommended_actions: list[str]


def run_gh(args: list[str], *, allow_failure: bool = False) -> str:
    proc = subprocess.run(
        ["gh", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0 and not allow_failure:
        raise RuntimeError(proc.stderr.strip() or f"gh {' '.join(args)} failed")
    if proc.returncode != 0:
        return ""
    return proc.stdout


def load_repos(owner: str, limit: int) -> list[dict[str, Any]]:
    fields = ",".join(README_FIELDS)
    out = run_gh(["repo", "list", owner, "--limit", str(limit), "--json", fields])
    return json.loads(out)


def load_readme(owner: str, repo: str) -> str:
    path = f"repos/{owner}/{repo}/readme"
    out = run_gh([ "api", path ], allow_failure=True)
    if not out:
        return ""
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return out
    content = payload.get("content", "")
    encoding = payload.get("encoding", "")
    if encoding == "base64" and content:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return ""


def words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:140]
    return ""


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.strip()[:140]
    return ""


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def audit_repo(owner: str, repo: dict[str, Any]) -> RepoAudit:
    name = repo["name"]
    readme = load_readme(owner, name)
    readme_word_count = words(readme)
    raw_topics = repo.get("repositoryTopics") or []
    topics = [topic["name"] for topic in raw_topics if topic.get("name")]
    description = repo.get("description") or ""
    homepage = repo.get("homepageUrl") or ""
    language = (repo.get("primaryLanguage") or {}).get("name") or ""
    findings: list[str] = []
    actions: list[str] = []
    score = 100

    if not readme:
        score -= 45
        findings.append("missing README")
        actions.append("Create a README with identity, quickstart, usage, development, and trust sections.")
    else:
        first = first_nonempty_line(readme)
        if first in {"---", "<!-- Add TLDR -->"} or first.startswith("<!--"):
            score -= 10
            findings.append("weak first rendered line")
            actions.append("Open with a human-facing project title and one-line outcome before metadata/comments.")
        if readme_word_count < 250:
            score -= 18
            findings.append("README is very thin")
            actions.append("Add concrete quickstart, usage example, and development/test commands.")
        elif readme_word_count < 500:
            score -= 8
            findings.append("README may be underdeveloped")
            actions.append("Check whether setup, usage, and contribution paths are complete.")
        if not first_heading(readme):
            score -= 8
            findings.append("missing markdown heading")
            actions.append("Add a clear H1 project title.")
        if not has_any(readme, [r"\bquick\s*start\b", r"\bgetting started\b", r"\binstallation\b", r"\bsetup\b"]):
            score -= 12
            findings.append("missing quickstart/setup section")
            actions.append("Add the fastest path to one useful local or hosted result.")
        if not has_any(readme, [r"\busage\b", r"\bexample\b", r"```", r"\bnpx\b", r"\bpython\b", r"\bnpm\b"]):
            score -= 10
            findings.append("missing concrete usage proof")
            actions.append("Add a real command, code snippet, screenshot, GIF, or example output.")
        if not has_any(readme, [r"\btest\b", r"\bbuild\b", r"\bdevelop", r"\bcontribut"]):
            score -= 8
            findings.append("weak developer onboarding")
            actions.append("Add local development and verification commands or link to contributor docs.")
        if not has_any(readme, [r"!\[", r"<img", r"\bdemo\b", r"\bscreenshot\b", r"\bexample output\b"]):
            score -= 5
            findings.append("no visual/demo/example artifact")
            actions.append("Add a screenshot, demo link, GIF, or example output if the project has a visible surface.")

    if not description:
        score -= 12
        findings.append("missing GitHub description")
        actions.append("Set a one-line About description using language/technology + project type + purpose.")
    if not homepage:
        score -= 4
        findings.append("missing homepage/demo URL")
        actions.append("Add a homepage, deployed app, docs page, or canonical project URL when one exists.")
    if len(topics) < 3:
        score -= 8
        findings.append("too few GitHub topics")
        actions.append("Add 5-10 public-safe topics for language, category, audience, and workflow.")

    score = max(0, min(100, score))
    severity = "good"
    if score < 50:
        severity = "critical"
    elif score < 70:
        severity = "needs-work"
    elif score < 85:
        severity = "polish"

    return RepoAudit(
        name=name,
        visibility="private" if repo.get("isPrivate") else "public",
        url=repo.get("url") or "",
        description=description,
        homepage=homepage,
        topics=topics,
        primary_language=language,
        pushed_at=repo.get("pushedAt") or "",
        readme_exists=bool(readme),
        readme_words=readme_word_count,
        first_heading=first_heading(readme),
        first_nonempty=first_nonempty_line(readme),
        score=score,
        severity=severity,
        findings=sorted(set(findings)),
        recommended_actions=list(dict.fromkeys(actions)),
    )


def render_markdown(owner: str, audits: list[RepoAudit]) -> str:
    lines = [
        f"# Repository README Audit: `{owner}`",
        "",
        "Generated by `repo-readme-onboarding-ops`.",
        "",
        "## Summary",
        "",
    ]
    counts: dict[str, int] = {}
    for audit in audits:
        counts[audit.severity] = counts.get(audit.severity, 0) + 1
    for severity in ["critical", "needs-work", "polish", "good"]:
        lines.append(f"- `{severity}`: {counts.get(severity, 0)}")
    lines.extend([
        "",
        "## Ranked Repos",
        "",
        "| Repo | Visibility | Score | Words | Findings |",
        "|---|---:|---:|---:|---|",
    ])
    for audit in sorted(audits, key=lambda item: (item.score, item.name.lower())):
        findings = ", ".join(audit.findings) if audit.findings else "none"
        lines.append(
            f"| [{audit.name}]({audit.url}) | {audit.visibility} | {audit.score} | "
            f"{audit.readme_words} | {findings} |"
        )
    lines.extend(["", "## Per-Repo Recommendations", ""])
    for audit in sorted(audits, key=lambda item: (item.score, item.name.lower())):
        lines.extend([
            f"### {audit.name}",
            "",
            f"- URL: {audit.url}",
            f"- Visibility: `{audit.visibility}`",
            f"- Score: `{audit.score}` (`{audit.severity}`)",
            f"- README words: `{audit.readme_words}`",
            f"- GitHub description: {audit.description or '`missing`'}",
            f"- Homepage: {audit.homepage or '`missing`'}",
            f"- Topics: {', '.join(audit.topics) if audit.topics else '`missing`'}",
            f"- First heading: {audit.first_heading or '`missing`'}",
            f"- First non-empty line: {audit.first_nonempty or '`missing`'}",
            "- Recommended actions:",
        ])
        for action in audit.recommended_actions or ["No immediate README action from heuristic audit."]:
            lines.append(f"  - {action}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True, help="GitHub owner or org to audit.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument("--out", help="Markdown output path.")
    parser.add_argument("--json-out", help="JSON output path.")
    args = parser.parse_args()

    repos = load_repos(args.owner, args.limit)
    if args.public_only:
        repos = [repo for repo in repos if not repo.get("isPrivate")]
    audits = [audit_repo(args.owner, repo) for repo in repos]
    markdown = render_markdown(args.owner, audits)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(markdown, encoding="utf-8")
    else:
        print(markdown)

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(
            json.dumps([asdict(audit) for audit in audits], indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
