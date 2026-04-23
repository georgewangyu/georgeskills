#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


MARKER_FILE = ".liferepo-private.json"
LOCAL_POINTER = Path(".liferepo") / "local" / "private_repo.json"
ENV_KEYS = ("LIFEREPO_PRIVATE_ROOT", "PRIVATE_REPO_ROOT")
EXCLUDED_SIBLINGS = {"liferepo", "georgeskills", ".git", ".github"}
LEGACY_HINTS = (
    "journal",
    "memory",
    "notes-private",
    "health-family",
    "personal-health",
    "projects",
    "openclaw",
    "TODO_AIDA.md",
    "SOUL.md",
)


def _env_candidate() -> Path | None:
    for key in ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        candidate = Path(value).expanduser().resolve()
        if candidate.exists():
            return candidate
    return None


def _pointer_from_liferepo_config(here: Path) -> Path | None:
    for parent in [here.parent, *here.parents]:
        liferepo = parent / "liferepo"
        pointer = liferepo / LOCAL_POINTER
        if not pointer.exists():
            continue
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
        except Exception:
            continue
        raw = str(data.get("private_repo_path", "")).strip()
        if raw:
            candidate = Path(raw).expanduser()
            if not candidate.is_absolute():
                candidate = (liferepo / candidate).resolve()
            else:
                candidate = candidate.resolve()
            if candidate.exists():
                return candidate

        private_name = str(data.get("private_repo_name", "")).strip()
        if private_name and "/" not in private_name and "\\" not in private_name:
            candidate = (liferepo.parent / private_name).resolve()
            if candidate.exists():
                return candidate
    return None


def _marker_candidate(here: Path) -> Path | None:
    for parent in [here.parent, *here.parents]:
        if (parent / MARKER_FILE).exists():
            return parent
    for parent in [here.parent, *here.parents]:
        try:
            for child in parent.iterdir():
                if child.is_dir() and (child / MARKER_FILE).exists():
                    return child
        except Exception:
            continue
    return None


def _legacy_sibling_candidate(here: Path) -> Path | None:
    for parent in [here.parent, *here.parents]:
        try:
            for child in parent.iterdir():
                if not child.is_dir() or child.name in EXCLUDED_SIBLINGS:
                    continue
                if (child / MARKER_FILE).exists():
                    return child
        except Exception:
            continue
    return None


def _legacy_workspace_candidate(here: Path) -> Path | None:
    for parent in [here.parent, *here.parents]:
        has_startup_router = (parent / "AGENTS.md").exists()
        if has_startup_router and any((parent / hint).exists() for hint in LEGACY_HINTS):
            return parent
    return None


def resolve_private_repo_root() -> Path:
    here = Path(__file__).resolve()
    for resolver in (
        _env_candidate,
        lambda: _pointer_from_liferepo_config(here),
        lambda: _marker_candidate(here),
        lambda: _legacy_sibling_candidate(here),
        lambda: _legacy_workspace_candidate(here),
    ):
        candidate = resolver()
        if candidate is not None:
            return candidate
    raise FileNotFoundError(
        "Could not resolve private repo root. Set LIFEREPO_PRIVATE_ROOT (or PRIVATE_REPO_ROOT)."
    )
