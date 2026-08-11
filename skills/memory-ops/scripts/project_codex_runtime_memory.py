#!/usr/bin/env python3
"""Project reviewed Codex automation memory into private memory candidates.

The projection is intentionally one-way. It inventories only
``automations/*/memory.md``, scans each complete file before parsing it, and
writes metadata/classification receipts rather than raw runtime prose.
Candidate text must come from a private, human-reviewed mapping and must point
to an existing durable source in the private repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from repo_paths import resolve_private_repo_root


CLASSIFICATIONS = {
    "runtime_cursor_status",
    "durable_fact_already_backed",
    "useful_candidate_lacking_durable_source",
    "ephemeral_noise",
    "sensitive_unsafe",
}

SECRET_PATTERNS = {
    "private_key_marker": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}\b"),
    "openai_like_key": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "slack_token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "google_api_key": re.compile(rb"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "bearer_token": re.compile(rb"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{20,}={0,2}"),
    "credential_assignment": re.compile(
        rb"(?i)\b(?:password|passwd|token|secret|api[_-]?key|client[_-]?secret|access[_-]?key)"
        rb"\b\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
}

REQUIRED_CANDIDATE_FIELDS = {
    "id",
    "type",
    "title",
    "summary",
    "entities",
    "date",
    "valid_from",
    "valid_to",
    "status",
    "durability",
    "strength",
    "last_reinforced_on",
    "source_ref",
    "tags",
    "supersedes",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def findings_for(data: bytes) -> list[str]:
    return sorted(label for label, pattern in SECRET_PATTERNS.items() if pattern.search(data))


def load_review_map(path: Path | None) -> dict[str, object]:
    if path is None:
        return {"version": 1, "files": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("review map must be an object with version=1")
    files = value.get("files")
    if not isinstance(files, dict):
        raise ValueError("review map files must be an object")
    return value


def source_path(private_root: Path, source_ref: str) -> Path:
    raw_path = source_ref.split("#", 1)[0].strip()
    path = Path(raw_path)
    if path.is_absolute():
        raise ValueError("candidate source_ref must be private-repo-relative")
    resolved = (private_root / path).resolve()
    if not is_within(resolved, private_root) or not resolved.is_file():
        raise ValueError(f"candidate source_ref is not an existing private file: {raw_path}")
    return resolved


def validate_candidate(candidate: dict[str, object], private_root: Path) -> None:
    missing = REQUIRED_CANDIDATE_FIELDS - set(candidate)
    if missing:
        raise ValueError(f"candidate {candidate.get('id', '<unknown>')} missing {sorted(missing)}")
    if candidate.get("status") != "candidate":
        raise ValueError("projected records must remain status=candidate")
    source_path(private_root, str(candidate["source_ref"]))
    serialized = json.dumps(candidate, ensure_ascii=False).encode("utf-8")
    labels = findings_for(serialized)
    if labels:
        raise ValueError(f"candidate {candidate['id']} failed secret scan: {labels}")


def classify_sections(
    automation_id: str,
    lines: list[str],
    review_entry: dict[str, object] | None,
) -> list[dict[str, object]]:
    sections = [] if review_entry is None else review_entry.get("sections", [])
    if not isinstance(sections, list):
        raise ValueError(f"{automation_id}: sections must be a list")
    covered: dict[int, str] = {}
    output: list[dict[str, object]] = []
    for raw in sections:
        if not isinstance(raw, dict):
            raise ValueError(f"{automation_id}: section must be an object")
        start = int(raw.get("start", 0))
        end = int(raw.get("end", 0))
        classification = str(raw.get("classification", ""))
        note = str(raw.get("note", "")).strip()
        if start < 1 or end < start or end > len(lines):
            raise ValueError(f"{automation_id}: invalid section range {start}-{end}")
        if classification not in CLASSIFICATIONS:
            raise ValueError(f"{automation_id}: invalid classification {classification!r}")
        for number in range(start, end + 1):
            if not lines[number - 1].strip():
                continue
            if number in covered:
                raise ValueError(f"{automation_id}: line {number} covered twice")
            covered[number] = classification
        section_bytes = ("\n".join(lines[start - 1 : end]) + "\n").encode("utf-8")
        output.append(
            {
                "line_start": start,
                "line_end": end,
                "classification": classification,
                "note": note,
                "sha256": sha256_bytes(section_bytes),
            }
        )
    expected = {number for number, line in enumerate(lines, start=1) if line.strip()}
    missing = sorted(expected - set(covered))
    if missing:
        raise ValueError(f"{automation_id}: unclassified non-empty lines {missing}")
    return output


def inventory_memory_files(
    codex_root: Path,
    review_map: dict[str, object],
    private_root: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    files_map = review_map["files"]
    assert isinstance(files_map, dict)
    inventory: list[dict[str, object]] = []
    candidates: list[dict[str, object]] = []
    for path in sorted((codex_root / "automations").glob("*/memory.md")):
        automation_id = path.parent.name
        data = path.read_bytes()
        file_findings = findings_for(data)
        file_stat = path.stat()
        record: dict[str, object] = {
            "automation_id": automation_id,
            "mode": stat.filemode(file_stat.st_mode),
            "size": file_stat.st_size,
            "mtime": datetime.fromtimestamp(file_stat.st_mtime).astimezone().isoformat(timespec="seconds"),
            "sha256": sha256_bytes(data),
            "secret_findings": file_findings,
            "content_read_for_classification": False,
            "sections": [],
        }
        review_entry = files_map.get(automation_id)
        if review_entry is not None and not isinstance(review_entry, dict):
            raise ValueError(f"{automation_id}: review entry must be an object")
        if not file_findings:
            lines = data.decode("utf-8").splitlines()
            record["content_read_for_classification"] = True
            record["sections"] = classify_sections(automation_id, lines, review_entry)
            raw_candidates = [] if review_entry is None else review_entry.get("candidates", [])
            if not isinstance(raw_candidates, list):
                raise ValueError(f"{automation_id}: candidates must be a list")
            for candidate in raw_candidates:
                if not isinstance(candidate, dict):
                    raise ValueError(f"{automation_id}: candidate must be an object")
                validate_candidate(candidate, private_root)
                candidates.append(candidate)
        inventory.append(record)
    unknown = sorted(set(files_map) - {item["automation_id"] for item in inventory})
    if unknown:
        raise ValueError(f"review map names absent automation memories: {unknown}")
    seen: set[str] = set()
    for candidate in candidates:
        record_id = str(candidate["id"])
        if record_id in seen:
            raise ValueError(f"duplicate candidate id: {record_id}")
        seen.add(record_id)
    return inventory, candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-root", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parser.add_argument("--private-repo-root")
    parser.add_argument("--review-map", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidate-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    private_root = (
        Path(args.private_repo_root).expanduser().resolve()
        if args.private_repo_root
        else resolve_private_repo_root()
    )
    codex_root = Path(args.codex_root).expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    candidate_path = args.candidate_output.expanduser().resolve()
    if not is_within(manifest_path, private_root):
        raise SystemExit("manifest must be inside the private repository")
    candidates_root = (private_root / "memory" / "candidates").resolve()
    if not is_within(candidate_path, candidates_root):
        raise SystemExit("candidate output must be under memory/candidates")
    review_map = load_review_map(args.review_map)
    inventory, candidates = inventory_memory_files(codex_root, review_map, private_root)
    manifest = {
        "schema": "codex-runtime-memory-projection-v1",
        "direction": "codex_runtime_to_private_candidates_only",
        "raw_memory_committed": False,
        "inventory_count": len(inventory),
        "secret_blocked_count": sum(bool(item["secret_findings"]) for item in inventory),
        "candidate_count": len(candidates),
        "files": inventory,
    }
    atomic_write(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    candidate_text = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in candidates)
    atomic_write(candidate_path, candidate_text)
    for item in inventory:
        findings = item["secret_findings"]
        suffix = f" blocked={','.join(findings)}" if findings else " clean"
        print(f"{item['automation_id']}:{suffix}")
    print(f"manifest={manifest_path}")
    print(f"candidates={candidate_path} count={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
