#!/usr/bin/env python3
"""
Experimental parser for Health Auto Export AutoSync sleep .hae files.

This is best-effort only:
- Some .hae files contain readable embedded text and can be partially decoded.
- Some .hae files (notably with bvx2 container) appear opaque in this workflow.

Output CSV columns:
  date,decoded,sleep_hours_raw,source_file
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from health_paths import sleep_hae_csv
from repo_paths import resolve_private_repo_root

DEFAULT_SLEEP_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~com~ifunography~HealthExport"
    / "Documents"
    / "AutoSync"
    / "HealthMetrics"
    / "sleep_analysis"
)

DEFAULT_OUT = (
    sleep_hae_csv(resolve_private_repo_root())
)


TOTAL_RE = re.compile(r"total[^0-9-]{0,12}([-+]?\d+(?:\.\d+)?)", re.IGNORECASE)


def extract_sleep_hours(text: str) -> str:
    """
    Find best candidate value after `total`.
    Filters to plausible hour values to avoid obvious binary artifacts.
    """
    candidates = TOTAL_RE.findall(text)
    for c in candidates:
        try:
            v = float(c)
        except ValueError:
            continue
        if 0.0 <= v <= 24.0:
            return f"{v:.6f}".rstrip("0").rstrip(".")
    return ""


def parse_file(fp: Path) -> tuple[str, str]:
    raw = fp.read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    sleep = extract_sleep_hours(text)
    decoded = "yes" if sleep else "no"
    return decoded, sleep


def file_date(fp: Path) -> str:
    name = fp.stem
    if len(name) == 8 and name.isdigit():
        return f"{name[:4]}-{name[4:6]}-{name[6:8]}"
    return name


def main() -> int:
    parser = argparse.ArgumentParser(description="Experimental .hae sleep parser")
    parser.add_argument("--sleep-dir", default=str(DEFAULT_SLEEP_DIR), help="Directory containing sleep_analysis/*.hae")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output CSV path")
    args = parser.parse_args()

    sleep_dir = Path(args.sleep_dir).expanduser()
    if not sleep_dir.exists():
        print(f"Sleep directory not found: {sleep_dir}")
        return 1

    files = sorted(sleep_dir.glob("*.hae"))
    if not files:
        print(f"No .hae files found in: {sleep_dir}")
        return 1

    rows = []
    decoded_count = 0
    for fp in files:
        decoded, sleep = parse_file(fp)
        if decoded == "yes":
            decoded_count += 1
        rows.append(
            {
                "date": file_date(fp),
                "decoded": decoded,
                "sleep_hours_raw": sleep,
                "source_file": str(fp),
            }
        )

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "decoded", "sleep_hours_raw", "source_file"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote: {out}")
    print(f"Decoded: {decoded_count}/{len(files)}")
    for r in rows[-10:]:
        print(f"- {r['date']}: decoded={r['decoded']} sleep_hours_raw={r['sleep_hours_raw'] or 'missing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
