#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_index(index_path: Path) -> dict[str, dict[str, object]]:
    if not index_path.exists():
        return {}
    try:
        value = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, dict[str, object]] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, dict):
            continue
        cleaned[key] = dict(item)
    return cleaned


def record_doc_access(
    *,
    private_repo_root: Path,
    source_path: Path,
    access_source: str,
    accessed_at: str | None = None,
) -> None:
    memory_dir = private_repo_root / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    index_path = memory_dir / "doc_access_index.json"
    log_path = memory_dir / "doc_access_log.jsonl"
    ts = accessed_at or _utc_now_iso()

    relative = source_path.relative_to(private_repo_root).as_posix()
    index = _load_index(index_path)
    current = dict(index.get(relative, {}))

    previous_count = current.get("access_count")
    access_count = int(previous_count) if isinstance(previous_count, int) else 0
    access_count += 1

    current["access_count"] = access_count
    current["last_accessed"] = ts
    current["last_access_source"] = access_source
    index[relative] = current

    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    event = {
        "path": relative,
        "access_source": access_source,
        "accessed_at": ts,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
