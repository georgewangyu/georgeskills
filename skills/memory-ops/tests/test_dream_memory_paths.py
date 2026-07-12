from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"


class DreamReportPathTest(unittest.TestCase):
    def test_doc_id_uses_configured_repo_name_and_report_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private_repo = Path(tmp) / "example-private"
            private_repo.mkdir()
            sys.path.insert(0, str(SCRIPT_DIR))
            try:
                with mock.patch.dict(
                    os.environ,
                    {"LIFEREPO_PRIVATE_ROOT": str(private_repo)},
                ):
                    spec = importlib.util.spec_from_file_location(
                        "dream_memory_test_module",
                        SCRIPT_DIR / "dream_memory.py",
                    )
                    assert spec and spec.loader
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            finally:
                sys.path.remove(str(SCRIPT_DIR))

            target = private_repo / "memory/reports/2026-07-11_dream.md"
            self.assertEqual(
                module.report_doc_id(target),
                "example-private/memory/reports/2026-07-11_dream",
            )


if __name__ == "__main__":
    unittest.main()
