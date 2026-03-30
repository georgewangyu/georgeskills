#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


STOPWORDS = {
    "ai",
    "app",
    "cloud",
    "co",
    "hq",
    "hub",
    "io",
    "labs",
    "ly",
    "os",
    "software",
    "tech",
}


@dataclass(frozen=True)
class Candidate:
    name: str
    slug: str
    words: int
    chars: int
    shape_score: int
    generic_penalty: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a compact naming worksheet from a text file of candidates."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Text file with one candidate name per line.",
    )
    parser.add_argument(
        "--tlds",
        default="com,io,app",
        help="Comma-separated TLDs to check. Default: com,io,app",
    )
    return parser.parse_args()


def normalize_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", name.lower())
    return slug


def estimate_shape_score(name: str, slug: str) -> int:
    score = 0
    length = len(slug)
    if 4 <= length <= 10:
        score += 2
    elif 11 <= length <= 14:
        score += 1

    if " " not in name.strip():
        score += 1

    vowels = sum(1 for char in slug if char in "aeiou")
    consonants = max(len(slug) - vowels, 1)
    ratio = vowels / consonants
    if 0.3 <= ratio <= 1.2:
        score += 1

    if re.search(r"(.)\1\1", slug):
        score -= 1

    if re.search(r"[0-9-]", name):
        score -= 1

    return max(score, 0)


def estimate_generic_penalty(name: str) -> int:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    return sum(1 for token in tokens if token in STOPWORDS)


def load_candidates(path: Path) -> list[Candidate]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    names = [line for line in lines if line and not line.startswith("#")]
    seen: set[str] = set()
    candidates: list[Candidate] = []
    for name in names:
        slug = normalize_slug(name)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        candidates.append(
            Candidate(
                name=name,
                slug=slug,
                words=len(name.split()),
                chars=len(slug),
                shape_score=estimate_shape_score(name, slug),
                generic_penalty=estimate_generic_penalty(name),
            )
        )
    return candidates


def build_domain_targets(slug: str, tlds: list[str]) -> str:
    return ", ".join(f"{slug}.{tld}" for tld in tlds)


def build_search_prompt(name: str, suffix: str) -> str:
    return f"\"{name}\" {suffix}".strip()


def main() -> int:
    args = parse_args()
    candidates = load_candidates(args.input)
    tlds = [part.strip().lstrip(".") for part in args.tlds.split(",") if part.strip()]

    print("# Naming Shortlist Worksheet")
    print()
    print("| Candidate | Slug | Words | Chars | Shape | Generic Penalty | Domains To Check | USPTO Query | Common-Law Query |")
    print("| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |")
    for candidate in candidates:
        domains = build_domain_targets(candidate.slug, tlds)
        uspto_query = build_search_prompt(candidate.name, "")
        common_law_query = build_search_prompt(candidate.name, "software OR app OR saas")
        print(
            f"| {candidate.name} | `{candidate.slug}` | {candidate.words} | {candidate.chars} | "
            f"{candidate.shape_score} | {candidate.generic_penalty} | {domains} | "
            f"`{uspto_query}` | `{common_law_query}` |"
        )

    print()
    print("## Notes")
    print()
    print("- `Shape` is a lightweight memorability heuristic, not a brand verdict.")
    print("- `Generic Penalty` counts common startup suffix words that tend to weaken distinctiveness.")
    print("- Use USPTO, state, web, and domain checks before treating any candidate as viable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
