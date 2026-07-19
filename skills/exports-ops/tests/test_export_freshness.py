from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = SKILL_ROOT / "scripts" / "audit_export_freshness.py"


class ExportFreshnessAuditTest(unittest.TestCase):
    def run_audit(self, registry: dict, now: str) -> dict:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            marker = root / "marker"
            manifest = root / "manifest.json"
            marker.write_text("2026-07-16T12:00:00+00:00\n", encoding="utf-8")
            manifest.write_text("{}\n", encoding="utf-8")
            registry["sources"]["gmail"]["freshness"]["markers"][0]["path"] = str(
                marker
            )
            registry["sources"]["facebook"]["manifest_path"] = str(manifest)
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_SCRIPT),
                    "--registry",
                    str(registry_path),
                    "--now",
                    now,
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(completed.stdout)

    def fixture(self) -> dict:
        return {
            "schema": "personal-data-export-freshness-v1",
            "updated_at_utc": "2026-07-16T12:00:00Z",
            "sources": {
                "gmail": {
                    "display_name": "Gmail",
                    "cadence_label": "daily",
                    "refresh_mode": "incremental_automatic",
                    "freshness": {
                        "type": "timestamp_markers",
                        "max_age_hours": 48,
                        "markers": [{"account": "test@example.com", "path": "unused"}],
                    },
                },
                "facebook": {
                    "display_name": "Facebook",
                    "cadence_label": "quarterly",
                    "refresh_mode": "manual",
                    "next_due_on": "2026-10-14",
                    "manifest_path": "unused",
                },
            },
        }

    def test_current_sources(self) -> None:
        result = self.run_audit(self.fixture(), "2026-07-17T00:00:00Z")
        self.assertEqual(result["attention_required"], [])
        self.assertEqual(result["sources"]["gmail"]["status"], "current")
        self.assertEqual(result["sources"]["facebook"]["status"], "current")
        self.assertTrue(result["sources"]["facebook"]["archive_available"])

    def test_stale_marker_and_due_snapshot(self) -> None:
        result = self.run_audit(self.fixture(), "2026-10-14T12:00:00Z")
        self.assertEqual(result["attention_required"], ["gmail", "facebook"])
        self.assertEqual(result["sources"]["gmail"]["status"], "stale")
        self.assertEqual(result["sources"]["facebook"]["status"], "due")


if __name__ == "__main__":
    unittest.main()
