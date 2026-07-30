#!/usr/bin/env python3
"""Score strategic lanes and allocate constrained sprint capacity."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_CORE_WEIGHTS = {
    "pnr": 0.22,
    "bp": 0.16,
    "ca": 0.26,
    "fit": 0.16,
    "align": 0.20,
}
DEFAULT_PENALTIES = {"oc": 0.12, "sat": 0.12}
DEFAULT_CONFIDENCE_FLOOR = 0.60
REQUIRED_SCORE_KEYS = set(DEFAULT_CORE_WEIGHTS) | {"ec", "oc", "sat"}


class InputError(ValueError):
    """Raised when allocator input is invalid."""


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{label} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise InputError(f"{label} must be finite")
    return value


def bounded(value: Any, label: str, low: float = 0, high: float = 100) -> float:
    value = number(value, label)
    if value < low or value > high:
        raise InputError(f"{label} must be between {low} and {high}")
    return value


def load_model(data: dict[str, Any]) -> dict[str, Any]:
    supplied = data.get("model", {})
    if not isinstance(supplied, dict):
        raise InputError("model must be an object")

    weights = supplied.get("core_weights", DEFAULT_CORE_WEIGHTS)
    penalties = supplied.get("penalties", DEFAULT_PENALTIES)
    confidence_floor = bounded(
        supplied.get("confidence_floor", DEFAULT_CONFIDENCE_FLOOR),
        "model.confidence_floor",
        0,
        1,
    )

    if not isinstance(weights, dict) or set(weights) != set(DEFAULT_CORE_WEIGHTS):
        raise InputError(
            "model.core_weights must contain exactly: "
            + ", ".join(DEFAULT_CORE_WEIGHTS)
        )
    clean_weights = {
        key: bounded(value, f"model.core_weights.{key}", 0, 1)
        for key, value in weights.items()
    }
    if not math.isclose(sum(clean_weights.values()), 1.0, abs_tol=1e-6):
        raise InputError("model.core_weights must sum to 1.0")

    if not isinstance(penalties, dict) or set(penalties) != set(DEFAULT_PENALTIES):
        raise InputError("model.penalties must contain exactly: oc, sat")
    clean_penalties = {
        key: bounded(value, f"model.penalties.{key}", 0, 1)
        for key, value in penalties.items()
    }

    return {
        "core_weights": clean_weights,
        "penalties": clean_penalties,
        "confidence_floor": confidence_floor,
    }


def validate_lanes(data: dict[str, Any]) -> list[dict[str, Any]]:
    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise InputError("lanes must be a non-empty array")
    if len(lanes) > 20:
        raise InputError("lanes must contain no more than 20 entries")

    clean: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, lane in enumerate(lanes):
        label = f"lanes[{index}]"
        if not isinstance(lane, dict):
            raise InputError(f"{label} must be an object")
        name = lane.get("name")
        if not isinstance(name, str) or not name.strip():
            raise InputError(f"{label}.name must be a non-empty string")
        name = name.strip()
        if name.casefold() in names:
            raise InputError(f"lane names must be unique: {name}")
        names.add(name.casefold())

        scores = lane.get("scores")
        if not isinstance(scores, dict) or set(scores) != REQUIRED_SCORE_KEYS:
            raise InputError(
                f"{label}.scores must contain exactly: "
                + ", ".join(sorted(REQUIRED_SCORE_KEYS))
            )
        clean_scores = {
            key: bounded(value, f"{label}.scores.{key}")
            for key, value in scores.items()
        }

        minimum = bounded(lane.get("min_pct", 0), f"{label}.min_pct")
        maximum = bounded(lane.get("max_pct", 100), f"{label}.max_pct")
        if minimum > maximum:
            raise InputError(f"{label}.min_pct must not exceed max_pct")
        if not math.isclose(minimum * 10, round(minimum * 10), abs_tol=1e-8):
            raise InputError(f"{label}.min_pct must use increments of 0.1")
        if not math.isclose(maximum * 10, round(maximum * 10), abs_tol=1e-8):
            raise InputError(f"{label}.max_pct must use increments of 0.1")

        evidence = lane.get("evidence", [])
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) and item.strip() for item in evidence
        ):
            raise InputError(f"{label}.evidence must be an array of non-empty strings")
        notes = lane.get("notes", "")
        if not isinstance(notes, str):
            raise InputError(f"{label}.notes must be a string")

        clean.append(
            {
                "name": name,
                "scores": clean_scores,
                "min_pct": minimum,
                "max_pct": maximum,
                "evidence": evidence,
                "notes": notes,
            }
        )

    if sum(lane["min_pct"] for lane in clean) > 100 + 1e-9:
        raise InputError("lane min_pct values must sum to no more than 100")
    if sum(lane["max_pct"] for lane in clean) < 100 - 1e-9:
        raise InputError("lane max_pct values must provide at least 100% capacity")
    return clean


def score_lane(lane: dict[str, Any], model: dict[str, Any]) -> dict[str, float]:
    scores = lane["scores"]
    core = sum(
        model["core_weights"][key] * scores[key]
        for key in model["core_weights"]
    )
    confidence_multiplier = model["confidence_floor"] + (
        1 - model["confidence_floor"]
    ) * scores["ec"] / 100
    opportunity_penalty = model["penalties"]["oc"] * scores["oc"]
    saturation_penalty = model["penalties"]["sat"] * scores["sat"]
    adjusted = max(
        0,
        min(
            100,
            core * confidence_multiplier
            - opportunity_penalty
            - saturation_penalty,
        ),
    )
    return {
        "core": core,
        "confidence_multiplier": confidence_multiplier,
        "opportunity_penalty": opportunity_penalty,
        "saturation_penalty": saturation_penalty,
        "adjusted": adjusted,
    }


def allocate(scored: list[dict[str, Any]]) -> tuple[list[float], list[str]]:
    allocations = [lane["min_pct"] for lane in scored]
    remaining = 100 - sum(allocations)
    warnings: list[str] = []

    while remaining > 1e-8:
        active = [
            index
            for index, lane in enumerate(scored)
            if allocations[index] < lane["max_pct"] - 1e-8
        ]
        if not active:
            raise InputError("allocation caps leave capacity undistributed")

        total_score = sum(scored[index]["calculation"]["adjusted"] for index in active)
        if total_score <= 1e-12:
            warnings.append(
                "All uncapped lanes had zero adjusted score; remaining capacity "
                "was distributed evenly within caps."
            )
            shares = {index: 1 / len(active) for index in active}
        else:
            shares = {
                index: scored[index]["calculation"]["adjusted"] / total_score
                for index in active
            }

        proposed = {index: remaining * shares[index] for index in active}
        capped = [
            index
            for index in active
            if proposed[index] >= scored[index]["max_pct"] - allocations[index] - 1e-10
        ]
        if capped:
            for index in capped:
                room = scored[index]["max_pct"] - allocations[index]
                allocations[index] += room
                remaining -= room
            continue

        for index in active:
            allocations[index] += proposed[index]
        remaining = 0

    return allocations, warnings


def rounded_allocations(
    exact: list[float], scored: list[dict[str, Any]]
) -> list[float]:
    rounded = [round(value, 1) for value in exact]
    delta_units = int(round((100 - sum(rounded)) * 10))

    while delta_units:
        direction = 1 if delta_units > 0 else -1
        candidates = []
        for index, value in enumerate(rounded):
            if direction > 0 and value + 0.1 <= scored[index]["max_pct"] + 1e-9:
                candidates.append(index)
            if direction < 0 and value - 0.1 >= scored[index]["min_pct"] - 1e-9:
                candidates.append(index)
        if not candidates:
            raise InputError("could not round allocations within floor/cap constraints")

        candidates.sort(
            key=lambda index: scored[index]["calculation"]["adjusted"],
            reverse=direction > 0,
        )
        rounded[candidates[0]] = round(rounded[candidates[0]] + direction * 0.1, 1)
        delta_units -= direction

    return rounded


def calculate(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise InputError("input root must be an object")
    model = load_model(data)
    lanes = validate_lanes(data)
    profile = data.get("profile", {})
    if not isinstance(profile, dict):
        raise InputError("profile must be an object")

    capacity_hours = profile.get("capacity_hours")
    if capacity_hours is not None:
        capacity_hours = number(capacity_hours, "profile.capacity_hours")
        if capacity_hours <= 0:
            raise InputError("profile.capacity_hours must be greater than zero")

    scored: list[dict[str, Any]] = []
    for lane in lanes:
        item = dict(lane)
        item["calculation"] = score_lane(lane, model)
        scored.append(item)

    exact, warnings = allocate(scored)
    allocations = rounded_allocations(exact, scored)

    results = []
    for lane, allocation in zip(scored, allocations):
        result = {
            "name": lane["name"],
            "adjusted_score": round(lane["calculation"]["adjusted"], 2),
            "core_score": round(lane["calculation"]["core"], 2),
            "confidence_multiplier": round(
                lane["calculation"]["confidence_multiplier"], 3
            ),
            "opportunity_cost_penalty": round(
                lane["calculation"]["opportunity_penalty"], 2
            ),
            "saturation_penalty": round(
                lane["calculation"]["saturation_penalty"], 2
            ),
            "allocation_pct": allocation,
            "min_pct": lane["min_pct"],
            "max_pct": lane["max_pct"],
            "evidence": lane["evidence"],
            "notes": lane["notes"],
        }
        if capacity_hours is not None:
            result["allocation_hours"] = round(capacity_hours * allocation / 100, 1)
        results.append(result)

    results.sort(key=lambda item: item["allocation_pct"], reverse=True)
    return {
        "profile": profile,
        "model": model,
        "warnings": warnings,
        "results": results,
        "total_allocation_pct": round(
            sum(item["allocation_pct"] for item in results), 1
        ),
    }


def to_markdown(result: dict[str, Any]) -> str:
    profile = result["profile"]
    title = profile.get("name", "Allocation")
    horizon = profile.get("horizon", "unspecified horizon")
    has_hours = any("allocation_hours" in item for item in result["results"])

    lines = [
        f"# Strategic capacity allocation: {title}",
        "",
        f"Horizon: {horizon}",
        "",
        "| Lane | Score | Allocation |"
        + (" Hours |" if has_hours else "")
        + " Floor–cap |",
        "|---|---:|---:|"
        + ("---:|" if has_hours else "")
        + "---:|",
    ]
    for item in result["results"]:
        row = (
            f"| {item['name']} | {item['adjusted_score']:.2f} | "
            f"{item['allocation_pct']:.1f}% |"
        )
        if has_hours:
            row += f" {item['allocation_hours']:.1f} |"
        row += f" {item['min_pct']:g}–{item['max_pct']:g}% |"
        lines.append(row)

    lines.extend(["", "## Audit"])
    for item in result["results"]:
        lines.append(
            f"- **{item['name']}**: core {item['core_score']:.2f}; "
            f"confidence ×{item['confidence_multiplier']:.3f}; "
            f"opportunity-cost penalty {item['opportunity_cost_penalty']:.2f}; "
            f"saturation penalty {item['saturation_penalty']:.2f}."
        )
    if result["warnings"]:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in result["warnings"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score strategic lanes and allocate constrained capacity."
    )
    parser.add_argument("input", type=Path, help="JSON input file")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="output format (default: json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = calculate(data)
    except (OSError, json.JSONDecodeError, InputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "markdown":
        print(to_markdown(result), end="")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
