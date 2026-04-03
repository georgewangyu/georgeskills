#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@(?:[A-Z0-9\-]+\.)+[A-Z]{2,}\b", re.IGNORECASE)
ABSOLUTE_PATH_RES = [
    re.compile(r"/Users/[^/\s]+"),
    re.compile(r"/home/[^/\s]+"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+"),
]
CONCRETE_PEOPLE_PATH_RE = re.compile(r"\bpeople/([a-z0-9][a-z0-9_-]{1,})/", re.IGNORECASE)
SECRET_RES = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
]
ALLOWLIST_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "localhost",
    "local",
    "test",
    "invalid",
    "users.noreply.github.com",
}
GENERIC_IDENTIFIER_ALLOWLIST = {
    "root",
    "admin",
    "user",
    "test",
    "example",
    "local",
    "localhost",
}
PEOPLE_PATH_ALLOWLIST = {"example", "person", "people", "sample", "template", "user"}


def git_output(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return proc.stdout


def staged_files() -> list[str]:
    output = git_output("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [item for item in output.split("\0") if item]


def is_binary(path: str) -> bool:
    output = git_output("diff", "--cached", "--numstat", "--", path).strip()
    if not output:
        return False
    first_line = output.splitlines()[0]
    parts = first_line.split("\t")
    return len(parts) >= 2 and parts[0] == "-" and parts[1] == "-"


def added_lines(path: str) -> list[tuple[int, str]]:
    patch = git_output("diff", "--cached", "--unified=0", "--no-color", "--", path)
    lines: list[tuple[int, str]] = []
    current_new_line = 0
    for raw_line in patch.splitlines():
        if raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw_line)
            if not match:
                continue
            current_new_line = int(match.group(1))
            continue
        if raw_line.startswith("+++ ") or raw_line.startswith("--- "):
            continue
        if raw_line.startswith("+"):
            lines.append((current_new_line, raw_line[1:]))
            current_new_line += 1
            continue
        if raw_line.startswith("-"):
            continue
        current_new_line += 1
    return lines


def identity_patterns() -> list[tuple[str, re.Pattern[str]]]:
    values: list[tuple[str, str]] = []
    home = str(Path.home())
    username = Path.home().name.strip()
    git_name = git_output("config", "--get", "user.name").strip()
    git_email = git_output("config", "--get", "user.email").strip()
    email_local = git_email.split("@", 1)[0].strip() if "@" in git_email else ""

    values.extend(
        [
            ("home path", home),
            ("home username", username),
            ("git user.name", git_name),
            ("git user.email", git_email),
            ("git email local part", email_local),
            ("$USER", os.environ.get("USER", "").strip()),
        ]
    )

    patterns: list[tuple[str, re.Pattern[str]]] = []
    seen: set[str] = set()
    for label, value in values:
        normalized = value.strip()
        lowered = normalized.lower()
        if len(normalized) < 4 or lowered in GENERIC_IDENTIFIER_ALLOWLIST or normalized in seen:
            continue
        seen.add(normalized)
        patterns.append((label, re.compile(re.escape(normalized), re.IGNORECASE)))
    return patterns


def line_has_non_placeholder_email(text: str) -> str | None:
    for match in EMAIL_RE.finditer(text):
        email = match.group(0)
        domain = email.split("@", 1)[1].lower()
        if domain in ALLOWLIST_EMAIL_DOMAINS:
            continue
        return email
    return None


def find_issues() -> list[str]:
    issues: list[str] = []
    identities = identity_patterns()
    files = staged_files()
    for path in files:
        if is_binary(path):
            continue
        is_validator_file = path == ".githooks/public-safety-check.py"
        for line_number, text in added_lines(path):
            for label, pattern in identities:
                if pattern.search(text):
                    issues.append(f"{path}:{line_number}: found local {label} in staged addition")
                    break

            found_email = line_has_non_placeholder_email(text)
            if found_email is not None:
                issues.append(f"{path}:{line_number}: found non-placeholder email '{found_email}'")

            if not is_validator_file:
                for pattern in ABSOLUTE_PATH_RES:
                    match = pattern.search(text)
                    if match:
                        issues.append(f"{path}:{line_number}: found absolute local path '{match.group(0)}'")
                        break

                people_match = CONCRETE_PEOPLE_PATH_RE.search(text)
                if people_match and people_match.group(1).lower() not in PEOPLE_PATH_ALLOWLIST:
                    issues.append(f"{path}:{line_number}: found concrete people path '{people_match.group(0)}'")

            for pattern in SECRET_RES:
                match = pattern.search(text)
                if match:
                    issues.append(f"{path}:{line_number}: found potential secret material '{match.group(0)[:32]}'")
                    break
    return issues


def main() -> int:
    try:
        files = staged_files()
    except subprocess.CalledProcessError as exc:
        print(f"public-safety-check: failed to inspect staged files: {exc}", file=sys.stderr)
        return 1

    if not files:
        return 0

    issues = find_issues()
    if not issues:
        return 0

    print("public-safety-check: blocked commit due to public-safety findings.", file=sys.stderr)
    for issue in issues:
        print(f"- {issue}", file=sys.stderr)
    print(
        "Fix the staged additions, or remove them from the commit before retrying.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
