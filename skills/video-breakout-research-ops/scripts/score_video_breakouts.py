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
    reach: float
    follows: float
    saves: float
    duration_seconds: float
    avg_watch_seconds: float
    post_age_days: float
    hook_text: str
    concept_summary: str
    post_url: str
    profile_continuity: float | None
    series_open_loop: float | None
    topic_profile_fit: float | None
    cta_type: str
    attribution: str
    cluster_key: str = ""
    asymmetry_score: float = 0.0
    engagement_rate: float = 0.0
    repeatability_bonus: float = 0.0
    recency_bonus: float = 0.0
    portability_bonus: float = 0.0
    weighted_score: float = 0.0
    follows_per_view: float = 0.0
    follows_per_reach: float = 0.0
    avg_watch_percentage: float = 0.0
    saves_per_view: float = 0.0
    shares_per_view: float = 0.0
    conversion_score: float = 0.0
    attribution_confidence: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank sampled video candidates by attention asymmetry and follower conversion."
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


def safe_unit_score(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return None
        labels = {
            "none": 0.0,
            "low": 0.2,
            "medium": 0.6,
            "moderate": 0.6,
            "high": 1.0,
        }
        if text in labels:
            return labels[text]
    score = safe_float(value)
    return min(max(score, 0.0), 1.0)


def attribution_confidence(attribution: str) -> float:
    return {
        "platform_first_party": 0.9,
        "creator_first_party": 0.75,
        "public_metadata": 0.6,
        "inferred": 0.35,
        "unknown": 0.2,
    }.get(attribution.strip().lower(), 0.2)


def normalized_signal(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return min(max(value / cap, 0.0), 1.0)


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
            reach=safe_float(row.get("reach") or row.get("accounts_reached")),
            follows=safe_float(row.get("follows")),
            saves=safe_float(row.get("saves")),
            duration_seconds=safe_float(row.get("duration_seconds")),
            avg_watch_seconds=safe_float(row.get("avg_watch_seconds")),
            post_age_days=safe_float(row.get("post_age_days")),
            hook_text=str(row.get("hook_text", "")).strip(),
            concept_summary=str(row.get("concept_summary", "")).strip(),
            post_url=str(row.get("post_url", "")).strip(),
            profile_continuity=safe_unit_score(row.get("profile_continuity")),
            series_open_loop=safe_unit_score(row.get("series_open_loop")),
            topic_profile_fit=safe_unit_score(row.get("topic_profile_fit")),
            cta_type=str(row.get("cta_type", "")).strip().lower() or "unknown",
            attribution=str(row.get("attribution", "")).strip().lower() or "unknown",
        )
        candidate.cluster_key = build_cluster_key(candidate.hook_text, candidate.concept_summary)
        candidate.asymmetry_score = math.log10(candidate.views + 1.0) - math.log10(candidate.followers + 1.0)
        total_engagement = candidate.likes + candidate.comments + candidate.shares
        candidate.engagement_rate = total_engagement / candidate.views if candidate.views > 0 else 0.0
        candidate.recency_bonus = recency_bonus(candidate.post_age_days)
        candidate.portability_bonus = portability_bonus(candidate.hook_text, candidate.concept_summary)
        apply_conversion_metrics(candidate)
        candidates.append(candidate)
    return candidates


def apply_conversion_metrics(candidate: CandidateRow) -> None:
    candidate.follows_per_view = candidate.follows / candidate.views if candidate.views > 0 else 0.0
    candidate.follows_per_reach = candidate.follows / candidate.reach if candidate.reach > 0 else 0.0
    candidate.avg_watch_percentage = (
        candidate.avg_watch_seconds / candidate.duration_seconds if candidate.duration_seconds > 0 else 0.0
    )
    candidate.saves_per_view = candidate.saves / candidate.views if candidate.views > 0 else 0.0
    candidate.shares_per_view = candidate.shares / candidate.views if candidate.views > 0 else 0.0
    candidate.attribution_confidence = attribution_confidence(candidate.attribution)

    weighted_signals: list[tuple[float, float]] = []
    if candidate.views > 0 and candidate.follows > 0:
        weighted_signals.append((normalized_signal(candidate.follows_per_view, 0.02), 30.0))
    if candidate.reach > 0 and candidate.follows > 0:
        weighted_signals.append((normalized_signal(candidate.follows_per_reach, 0.03), 20.0))
    if candidate.duration_seconds > 0 and candidate.avg_watch_seconds > 0:
        weighted_signals.append((normalized_signal(candidate.avg_watch_percentage, 0.70), 15.0))
    if candidate.views > 0 and candidate.saves > 0:
        weighted_signals.append((normalized_signal(candidate.saves_per_view, 0.01), 10.0))
    if candidate.views > 0 and candidate.shares > 0:
        weighted_signals.append((normalized_signal(candidate.shares_per_view, 0.005), 10.0))
    for value, weight in (
        (candidate.profile_continuity, 5.0),
        (candidate.series_open_loop, 5.0),
        (candidate.topic_profile_fit, 5.0),
    ):
        if value is not None:
            weighted_signals.append((value, weight))

    total_weight = sum(weight for _, weight in weighted_signals)
    if total_weight > 0:
        candidate.conversion_score = 100.0 * sum(value * weight for value, weight in weighted_signals) / total_weight


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


def conversion_mode(cta_type: str) -> str:
    return {
        "none": "content-led/no explicit CTA",
        "implicit_series": "implicit series",
        "direct_follow": "direct follow",
        "keyword_dm": "hybrid keyword-DM",
        "follow_gated_asset": "funnel-contaminated",
    }.get(cta_type, "unknown")


def format_percent(value: float, available: bool) -> str:
    return f"{value * 100:.2f}%" if available else "n/a"


def render_conversion_table(candidates: list[CandidateRow], top_n: int) -> list[str]:
    eligible = [row for row in candidates if row.follows > 0]
    lines = []
    lines.append(
        "| Rank | Platform | Creator | Follows | Follows/View | Follows/Reach | Avg Watch | Saves/View | Shares/View | Signal | CTA mode | Evidence |"
    )
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    for index, row in enumerate(
        sorted(eligible, key=lambda item: item.conversion_score, reverse=True)[:top_n], start=1
    ):
        evidence = f"{row.attribution} ({row.attribution_confidence:.2f})"
        lines.append(
            f"| {index} | {row.platform} | @{row.creator_handle} | {int(row.follows)} | "
            f"{format_percent(row.follows_per_view, row.views > 0)} | "
            f"{format_percent(row.follows_per_reach, row.reach > 0)} | "
            f"{format_percent(row.avg_watch_percentage, row.duration_seconds > 0 and row.avg_watch_seconds > 0)} | "
            f"{format_percent(row.saves_per_view, row.views > 0 and row.saves > 0)} | "
            f"{format_percent(row.shares_per_view, row.views > 0 and row.shares > 0)} | "
            f"{row.conversion_score:.1f} | {conversion_mode(row.cta_type)} | {evidence} |"
        )
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
    conversion_candidates = [row for row in candidates if row.follows > 0]
    if conversion_candidates:
        print("## Follower Conversion Candidates")
        print()
        for line in render_conversion_table(conversion_candidates, args.top):
            print(line)
        print()
    print("## Notes")
    print()
    print("- `Asym.` is `log10(views + 1) - log10(followers + 1)`. Higher means stronger reach relative to current base.")
    print("- `Score` adds repeatability, recency, portability, and a small engagement proxy, then penalizes larger creator bases.")
    print("- `Signal` is a 0-100 follower-conversion triage score normalized over only the available metrics; compare similar formats and inspect the underlying ratios.")
    print("- Evidence confidence is separate from conversion strength. Creator-provided insights are first-party claims, not independently audited results.")
    print("- Keyword-DM and follow-gated CTAs are labeled as hybrid or funnel-contaminated; observed follows are not assumed to be content-only conversion.")
    print("- Treat this output as a triage artifact. Manual review still matters for false positives, hidden fame, and stale trend formats.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
