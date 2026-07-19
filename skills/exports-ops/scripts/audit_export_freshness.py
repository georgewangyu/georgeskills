#!/usr/bin/env python3
"""Read-only audit of a personal-data export freshness registry."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def parse_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a UTC offset: {value}")
    return parsed.astimezone(timezone.utc)


def resolve_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def audit_markers(source: dict[str, Any], now: datetime) -> dict[str, Any]:
    freshness = source["freshness"]
    max_age_hours = float(freshness["max_age_hours"])
    marker_results: list[dict[str, Any]] = []
    status = "current"

    for marker in freshness.get("markers", []):
        path = resolve_path(marker["path"])
        result: dict[str, Any] = {
            "account": marker.get("account"),
            "path": str(path),
        }
        if not path.is_file():
            result["status"] = "missing"
            result["timestamp_utc"] = None
            result["age_hours"] = None
            status = "missing"
        else:
            timestamp = parse_datetime(path.read_text(encoding="utf-8").strip())
            age_hours = max(0.0, (now - timestamp).total_seconds() / 3600)
            result["timestamp_utc"] = timestamp.isoformat().replace("+00:00", "Z")
            result["age_hours"] = round(age_hours, 2)
            result["status"] = "current" if age_hours <= max_age_hours else "stale"
            if result["status"] == "stale" and status != "missing":
                status = "stale"
        marker_results.append(result)

    if not marker_results:
        status = "missing"

    return {
        "status": status,
        "cadence_label": source.get("cadence_label"),
        "refresh_mode": source.get("refresh_mode"),
        "max_age_hours": max_age_hours,
        "markers": marker_results,
        "review_action": source.get("review_action"),
    }


def audit_snapshot(source: dict[str, Any], today: date) -> dict[str, Any]:
    due_on_value = source.get("next_due_on")
    due_on = date.fromisoformat(due_on_value) if due_on_value else None
    status = "due" if due_on is not None and today >= due_on else "current"
    manifest_value = source.get("manifest_path")
    manifest_path = resolve_path(manifest_value) if manifest_value else None

    return {
        "status": status,
        "cadence_label": source.get("cadence_label"),
        "refresh_mode": source.get("refresh_mode"),
        "snapshot_date_local": source.get("snapshot_date_local"),
        "captured_at_utc": source.get("captured_at_utc"),
        "source_data_through_utc": source.get("source_data_through_utc"),
        "verified_at_utc": source.get("verified_at_utc"),
        "next_due_on": due_on_value,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "archive_available": manifest_path.is_file() if manifest_path else None,
        "review_action": source.get("review_action"),
    }


def audit_registry(registry: dict[str, Any], now: datetime) -> dict[str, Any]:
    if registry.get("schema") != "personal-data-export-freshness-v1":
        raise ValueError("unsupported or missing registry schema")
    sources = registry.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("registry must contain a non-empty sources object")

    results: dict[str, Any] = {}
    for source_id, source in sources.items():
        display_name = source.get("display_name", source_id)
        freshness = source.get("freshness", {})
        if freshness.get("type") == "timestamp_markers":
            result = audit_markers(source, now)
        else:
            result = audit_snapshot(source, now.date())
        result["display_name"] = display_name
        results[source_id] = result

    attention = [
        source_id
        for source_id, result in results.items()
        if result["status"] in {"due", "stale", "missing"}
    ]
    return {
        "schema": "personal-data-export-freshness-audit-v1",
        "as_of_utc": now.isoformat().replace("+00:00", "Z"),
        "registry_updated_at_utc": registry.get("updated_at_utc"),
        "attention_required": attention,
        "sources": results,
    }


def render_text(audit: dict[str, Any]) -> str:
    lines = [f"Personal data export freshness as of {audit['as_of_utc']}"]
    for source_id, result in audit["sources"].items():
        detail = f"cadence={result.get('cadence_label', 'unknown')}"
        if "markers" in result:
            marker_detail = ", ".join(
                f"{item.get('account') or 'marker'}={item['status']}"
                + (
                    f" ({item['age_hours']:.1f}h)"
                    if item.get("age_hours") is not None
                    else ""
                )
                for item in result["markers"]
            )
            detail += f"; {marker_detail or 'no markers configured'}"
        else:
            detail += f"; next_due={result.get('next_due_on') or 'unset'}"
            available = result.get("archive_available")
            if available is not None:
                detail += f"; archive={'available' if available else 'unavailable'}"
        lines.append(
            f"- {result['display_name']} [{source_id}]: {result['status']} ({detail})"
        )
    if audit["attention_required"]:
        lines.append("Attention: " + ", ".join(audit["attention_required"]))
    else:
        lines.append("Attention: none")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument(
        "--now",
        help="Override the audit time with an offset-aware ISO-8601 timestamp.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        now = parse_datetime(args.now) if args.now else datetime.now(timezone.utc)
        audit = audit_registry(registry, now)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"freshness audit failed: {error}", file=sys.stderr)
        return 2

    if args.json:
        json.dump(audit, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(render_text(audit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
