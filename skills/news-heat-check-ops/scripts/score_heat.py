#!/usr/bin/env python3
"""Calculate heuristic news attention and audience-fit scores from JSON."""

import argparse
import json
import sys
from pathlib import Path


ATTENTION_WEIGHTS = {
    "social_velocity": 0.30,
    "audience_breakout": 0.20,
    "cross_platform_spread": 0.20,
    "discussion_depth": 0.15,
    "acceleration": 0.15,
}

FIT_WEIGHTS = {
    "audience_relevance": 0.25,
    "demoability": 0.20,
    "novelty": 0.20,
    "distinctive_angle": 0.20,
    "actionability": 0.15,
}


def bounded_number(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be a number from 0 to 100")
    if value < 0 or value > 100:
        raise ValueError(f"{field} must be between 0 and 100")
    return float(value)


def weighted_score(values, weights, group):
    missing = [key for key in weights if key not in values]
    if missing:
        raise ValueError(f"{group} missing fields: {', '.join(missing)}")
    return round(
        sum(bounded_number(values[key], f"{group}.{key}") * weight for key, weight in weights.items()),
        1,
    )


def editorial_action(heat, fit):
    if heat >= 90 and fit >= 75:
        return "drop-everything"
    if heat >= 70 and fit >= 65:
        return "single segment"
    if heat >= 45 and fit >= 60:
        return "mention"
    return "ignore"


def stage(heat, acceleration):
    if heat < 45:
        return "watch"
    if acceleration < 25:
        return "cooling"
    if heat >= 80 and acceleration < 50:
        return "peaking"
    if heat >= 70:
        return "hot"
    if acceleration >= 50:
        return "rising"
    return "watch"


def score_item(item):
    if not isinstance(item, dict):
        raise ValueError("each input item must be an object")
    attention = item.get("attention", {})
    audience_fit = item.get("audience_fit", {})
    heat = weighted_score(attention, ATTENTION_WEIGHTS, "attention")
    fit = weighted_score(audience_fit, FIT_WEIGHTS, "audience_fit")
    acceleration = bounded_number(attention.get("acceleration"), "attention.acceleration")
    return {
        "topic": item.get("topic", "untitled topic"),
        "attention_heat": heat,
        "audience_fit": fit,
        "stage": stage(heat, acceleration),
        "recommended_action": editorial_action(heat, fit),
        "scoring_version": "news-heat-heuristic-v1",
    }


def load_input(path):
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="JSON file or - for stdin")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    try:
        payload = load_input(args.input)
        result = [score_item(item) for item in payload] if isinstance(payload, list) else score_item(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    json.dump(result, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
