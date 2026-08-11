from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location(
    "project_codex_runtime_memory_test_module",
    SCRIPT_DIR / "project_codex_runtime_memory.py",
)
assert SPEC and SPEC.loader
sys.path.insert(0, str(SCRIPT_DIR))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sys.path.remove(str(SCRIPT_DIR))


class CodexRuntimeMemoryProjectionTest(unittest.TestCase):
    def test_projection_omits_raw_text_and_blocks_secret_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex = root / "codex"
            private = root / "private"
            clean = codex / "automations" / "clean-run" / "memory.md"
            blocked = codex / "automations" / "blocked-run" / "memory.md"
            clean.parent.mkdir(parents=True)
            blocked.parent.mkdir(parents=True)
            clean.write_text("# Memory\n\n- durable but private runtime sentence\n", encoding="utf-8")
            blocked.write_text("token=abcdefghijklmnopqrstuvwxyz012345\n", encoding="utf-8")
            source = private / "docs" / "source.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Durable source\n", encoding="utf-8")

            review_map = {
                "version": 1,
                "files": {
                    "clean-run": {
                        "sections": [
                            {
                                "start": 1,
                                "end": 3,
                                "classification": "durable_fact_already_backed",
                                "note": "Backed by the reviewed source.",
                            }
                        ],
                        "candidates": [
                            {
                                "id": "status_change_test_projection_2026_08_10",
                                "type": "status_change",
                                "title": "Projection test",
                                "summary": "A reviewed, source-backed test record.",
                                "entities": ["memory-ops"],
                                "date": "2026-08-10",
                                "valid_from": "2026-08-10",
                                "valid_to": None,
                                "status": "candidate",
                                "durability": "active",
                                "strength": 3,
                                "last_reinforced_on": "2026-08-10",
                                "source_ref": "docs/source.md#durable-source",
                                "tags": ["memory", "projection"],
                                "supersedes": [],
                            }
                        ],
                    }
                },
            }
            inventory, candidates = MODULE.inventory_memory_files(codex, review_map, private)
            serialized = json.dumps(inventory)
            self.assertNotIn("durable but private runtime sentence", serialized)
            self.assertEqual(len(candidates), 1)
            blocked_record = next(item for item in inventory if item["automation_id"] == "blocked-run")
            self.assertFalse(blocked_record["content_read_for_classification"])
            self.assertEqual(blocked_record["secret_findings"], ["credential_assignment"])

    def test_requires_complete_nonempty_line_coverage(self) -> None:
        with self.assertRaisesRegex(ValueError, "unclassified non-empty lines"):
            MODULE.classify_sections(
                "example",
                ["# Header", "", "- result"],
                {
                    "sections": [
                        {
                            "start": 1,
                            "end": 1,
                            "classification": "runtime_cursor_status",
                            "note": "Header only.",
                        }
                    ]
                },
            )


if __name__ == "__main__":
    unittest.main()
