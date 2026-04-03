#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def _first_existing(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _legacy_health_family_records_root(private_repo_root: Path) -> Path | None:
    health_family_root = private_repo_root / "health-family"
    if not health_family_root.exists():
        return None
    direct_records = health_family_root / "records"
    if direct_records.exists():
        return direct_records
    for child in sorted(health_family_root.iterdir()):
        candidate = child / "records"
        if child.is_dir() and candidate.exists():
            return candidate
    return None


def _people_health_records_root(private_repo_root: Path) -> Path | None:
    people_root = private_repo_root / "people"
    if not people_root.exists():
        return None
    for child in sorted(people_root.iterdir()):
        candidate = child / "health" / "records"
        if child.is_dir() and candidate.exists():
            return candidate
    return None


def resolve_health_source_records_root(private_repo_root: Path) -> Path:
    env_path = _env_path("LIFEREPO_HEALTH_SOURCE_ROOT")
    if env_path is not None:
        return env_path

    people_candidate = _people_health_records_root(private_repo_root)
    candidates = [
        people_candidate,
        private_repo_root / "health-data" / "source-records",
        private_repo_root / "personal-health" / "records",
    ]
    existing = _first_existing([candidate for candidate in candidates if candidate is not None])
    return existing or private_repo_root / "health-data" / "source-records"


def resolve_health_records_root(private_repo_root: Path) -> Path:
    env_path = _env_path("LIFEREPO_HEALTH_RECORDS_ROOT")
    if env_path is not None:
        return env_path

    people_candidate = _people_health_records_root(private_repo_root)
    candidates = [
        people_candidate,
        private_repo_root / "health-data" / "records",
    ]
    legacy_candidate = _legacy_health_family_records_root(private_repo_root)
    existing = _first_existing([candidate for candidate in candidates if candidate is not None])
    return existing or legacy_candidate or private_repo_root / "health-data" / "records"


def daily_health_metrics_csv(private_repo_root: Path) -> Path:
    return resolve_health_records_root(private_repo_root) / "daily_health_metrics.csv"


def health_auto_export_raw_dir(private_repo_root: Path) -> Path:
    return resolve_health_records_root(private_repo_root) / "health_auto_export_raw"


def apple_health_export_xml(private_repo_root: Path) -> Path:
    return resolve_health_source_records_root(private_repo_root) / "apple_health_export" / "export.xml"
