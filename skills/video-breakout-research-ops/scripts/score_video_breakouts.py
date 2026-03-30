#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "our",
    "so",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
    "you",
    "your",
}


@dataclass
class CandidateRow:
    platform: str
    creator_handle: str
    followers: float
    views: float
    likes: float
    comments: float
    shares: float
    post_age_days: float
    hook_text: str
    concept_summary: str
    post_url: str
    cluster_key: str = ""
    asymmetry_score: float = 0.0
    engagement_rate: float = 0.0
    repeatability_bonus: float = 0.0
    recency_bonus: float = 0.0
    portability_bonus: float = 0.0
    weighted_score: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank sampled short-form video candidates by breakout asymmetry."
    )
    parser.add_argument("input", type=Path, help="CSV or JSONL file of sampled creators/posts")
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of ranked rows to include in the main table. Default: 15",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=8,
        help="Maximum number of concept clusters to print. Default: 8",
    )
    return parser.parse_args()


def safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace(",", "")
    if not text:
        return 0.0
    multiplier = 1.0
    if text.endswith("k"):
        multiplier = 1_000.0
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1_000_000.0
        text = text[:-1]
    elif text.endswith("b"):
        multiplier = 1_000_000_000.0
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return 0.0


def load_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    raise SystemExit("Input must be .csv, .jsonl, or .ndjson")


def normalize_text(*parts: str) -> str:
    text = " ".join(part for part in parts if part).lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    tokens = [token for token in tokens if token not in STOPWORDS and len(token) > 2]
    return " ".join(tokens)


def build_cluster_key(hook_text: str, concept_summary: str) -> str:
    normalized = normalize_text(hook_text, concept_summary)
    if not normalized:
        return "uncategorized"
    tokens = normalized.split()
    return " ".join(tokens[:6])


def portability_bonus(hook_text: str, concept_summary: str) -> float:
    text = f"{hook_text} {concept_summary}".lower()
    score = 0.0
    if any(token in text for token in {"how to", "mistakes", "before you", "3 ways", "steps"}):
        score += 0.35
    if any(token in text for token in {"storytime", "day in my life", "with my boyfriend", "grwm"}):
        score -= 0.2
    if any(token in text for token in {"template", "formula", "checklist", "framework"}):
        score += 0.2
    return score


def recency_bonus(post_age_days: float) -> float:
    if post_age_days <= 0:
        return 0.15
    if post_age_days <= 7:
        return 0.15
    if post_age_days <= 30:
        return 0.08
    if post_age_days <= 90:
        return 0.02
    return -0.05


def build_candidates(raw_rows: list[dict[str, Any]]) -> list[CandidateRow]:
    candidates: list[CandidateRow] = []
    for row in raw_rows:
        candidate = CandidateRow(
            platform=str(row.get("platform", "")).strip() or "unknown",
            creator_handle=str(row.get("creator_handle", "")).strip() or "unknown",
            followers=safe_float(row.get("followers")),
            views=safe_float(row.get("views")),
            likes=safe_float(row.get("likes")),
            comments=safe_float(row.get("comments")),
            shares=safe_float(row.get("shares")),
            post_age_days=safe_float(row.get("post_age_days")),
            hook_text=str(row.get("hook_text", "")).strip(),
            concept_summary=str(row.get("concept_summary", "")).strip(),
            post_url=str(row.get("post_url", "")).strip(),
        )
        candidate.cluster_key = build_cluster_key(candidate.hook_text, candidate.concept_summary)
        candidate.asymmetry_score = math.log10(candidate.views + 1.0) - math.log10(candidate.followers + 1.0)
        total_engagement = candidate.likes + candidate.comments + candidate.shares
        candidate.engagement_rate = total_engagement / candidate.views if candidate.views > 0 else 0.0
        candidate.recency_bonus = recency_bonus(candidate.post_age_days)
        candidate.portability_bonus = portability_bonus(candidate.hook_text, candidate.concept_summary)
        candidates.append(candidate)
    return candidates


def apply_repeatability(candidates: list[CandidateRow]) -> None:
    by_creator: dict[tuple[str, str], list[CandidateRow]] = defaultdict(list)
    for candidate in candidates:
        by_creator[(candidate.platform.lower(), candidate.creator_handle.lower())].append(candidate)

    for creator_rows in by_creator.values():
        strong_posts = sum(1 for row in creator_rows if row.asymmetry_score >= 1.0)
        bonus = min(max(strong_posts - 1, 0) * 0.12, 0.36)
        for row in creator_rows:
            row.repeatability_bonus = bonus


def apply_weighted_scores(candidates: list[CandidateRow]) -> None:
    for row in candidates:
        engagement_bonus = min(row.engagement_rate * 3.0, 0.25)
        large_base_penalty = 0.0
        if row.followers >= 100_000:
            large_base_penalty = 0.2
        elif row.followers >= 50_000:
            large_base_penalty = 0.1
        row.weighted_score = (
            row.asymmetry_score
            + row.repeatability_bonus
            + row.recency_bonus
            + row.portability_bonus
            + engagement_bonus
            - large_base_penalty
        )


def render_ranked_table(candidates: list[CandidateRow], top_n: int) -> list[str]:
    lines = []
    lines.append("| Rank | Platform | Creator | Followers | Views | Asym. | Score | Cluster | Evidence |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |")
    for index, row in enumerate(sorted(candidates, key=lambda item: item.weighted_score, reverse=True)[:top_n], start=1):
        evidence = row.hook_text or row.concept_summary or row.post_url or "n/a"
        evidence = evidence.replace("|", "/")[:80]
        lines.append(
            f"| {index} | {row.platform} | @{row.creator_handle} | {int(row.followers)} | {int(row.views)} | "
            f"{row.asymmetry_score:.2f} | {row.weighted_score:.2f} | {row.cluster_key} | {evidence} |"
        )
    return lines


def render_clusters(candidates: list[CandidateRow], limit: int) -> list[str]:
    clusters: dict[str, list[CandidateRow]] = defaultdict(list)
    for candidate in candidates:
        clusters[candidate.cluster_key].append(candidate)

    ranked_clusters = sorted(
        clusters.items(),
        key=lambda item: max(row.weighted_score for row in item[1]),
        reverse=True,
    )[:limit]

    lines = []
    for cluster_key, rows in ranked_clusters:
        top_score = max(row.weighted_score for row in rows)
        creators = ", ".join(sorted({f"{row.platform} @{row.creator_handle}" for row in rows})[:4])
        sample = max(rows, key=lambda row: row.weighted_score)
        lines.append(f"### {cluster_key}")
        lines.append("")
        lines.append(f"- Evidence count: `{len(rows)}`")
        lines.append(f"- Best weighted score: `{top_score:.2f}`")
        lines.append(f"- Example creators: {creators or 'n/a'}")
        lines.append(f"- Sample hook: {sample.hook_text or sample.concept_summary or 'n/a'}")
        lines.append(f"- Portability note: {portability_note(sample)}")
        lines.append("")
    return lines


def portability_note(row: CandidateRow) -> str:
    if row.portability_bonus >= 0.35:
        return "High portability. The hook looks instruction-led or framework-led rather than identity-led."
    if row.portability_bonus >= 0.1:
        return "Moderate portability. The concept looks adaptable with some niche rewriting."
    if row.portability_bonus <= -0.1:
        return "Low portability. The payoff appears tightly coupled to the creator's persona or life context."
    return "Mixed portability. Manual review needed before borrowing the format."


def main() -> int:
    args = parse_args()
    raw_rows = load_rows(args.input)
    if not raw_rows:
        raise SystemExit("No rows found in input file")

    candidates = build_candidates(raw_rows)
    apply_repeatability(candidates)
    apply_weighted_scores(candidates)
    ranked = sorted(candidates, key=lambda item: item.weighted_score, reverse=True)

    print("# Video Breakout Shortlist")
    print()
    print(f"- Rows analyzed: `{len(candidates)}`")
    print(f"- Unique creators: `{len({(row.platform, row.creator_handle) for row in candidates})}`")
    print(f"- Unique concept clusters: `{len({row.cluster_key for row in candidates})}`")
    print()
    print("## Ranked Candidates")
    print()
    for line in render_ranked_table(ranked, args.top):
        print(line)
    print()
    print("## Concept Clusters")
    print()
    for line in render_clusters(ranked, args.clusters):
        print(line)
    print("## Notes")
    print()
    print("- `Asym.` is `log10(views + 1) - log10(followers + 1)`. Higher means stronger reach relative to current base.")
    print("- `Score` adds repeatability, recency, portability, and a small engagement proxy, then penalizes larger creator bases.")
    print("- Treat this output as a triage artifact. Manual review still matters for false positives, hidden fame, and stale trend formats.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
