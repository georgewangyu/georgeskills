from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_history.py"
)
SPEC = importlib.util.spec_from_file_location("validate_history", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ValidateHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in MODULE.REQUIRED_ROOT_FILES:
            write(self.root / relative, "# Placeholder\n")
        self.record = (
            self.root
            / "history"
            / "2026"
            / "2026-07-27_example-video.md"
        )
        write(
            self.root / "history" / "INDEX.md",
            "[detailed](2026/2026-07-27_example-video.md)\n",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invoke_validator(self) -> tuple[int, str]:
        output = io.StringIO()
        with patch.object(
            sys,
            "argv",
            ["validate_history.py", self.root.as_posix()],
        ), redirect_stdout(output):
            result = MODULE.main()
        return result, output.getvalue()

    def run_validator(self, schema: str) -> tuple[int, str]:
        record_text = (
            "---\n"
            f"schema: {schema}\n"
            "video_id: 2026-07-27_example-video\n"
            "title: Example\n"
            "reviewed_at: 2026-07-27\n"
            "status: reviewable\n"
            "lesson_status: candidate\n"
            "tags: [example]\n"
            "---\n"
            "## Evidence\n\n"
            "## Creator Feedback\n\n"
            "## Failure Analysis\n\n"
            "## Reusable Lessons\n\n"
            "## Next Iteration\n"
        )
        write(self.record, record_text)
        return self.invoke_validator()

    def test_expected_schema_passes(self) -> None:
        result, output = self.run_validator("video-edit-history-v1")
        self.assertEqual(result, 0)
        self.assertIn("OK: 1 history records", output)

    def test_unexpected_schema_fails(self) -> None:
        result, output = self.run_validator("video-edit-history-v2")
        self.assertEqual(result, 1)
        self.assertIn("unexpected schema video-edit-history-v2", output)

    def test_plain_text_path_does_not_count_as_index_link(self) -> None:
        write(
            self.root / "history" / "INDEX.md",
            "Needs linking: 2026/2026-07-27_example-video.md\n",
        )
        result, output = self.run_validator("video-edit-history-v1")
        self.assertEqual(result, 1)
        self.assertIn("missing link from history/INDEX.md", output)

    def test_detailed_record_symlink_escape_fails(self) -> None:
        self.run_validator("video-edit-history-v1")
        outside = Path(self.temp.name).parent / (
            f"{Path(self.temp.name).name}-outside-record.md"
        )
        self.addCleanup(outside.unlink, missing_ok=True)
        write(outside, self.record.read_text(encoding="utf-8"))
        self.record.unlink()
        self.record.symlink_to(outside)
        result, output = self.invoke_validator()
        self.assertEqual(result, 1)
        self.assertIn("detailed record resolves outside history/", output)

    def test_history_directory_symlink_escape_fails(self) -> None:
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside_history = Path(outside_temp.name)
        write(outside_history / "INDEX.md", "# Index\n")
        (self.root / "history" / "INDEX.md").unlink()
        (self.root / "history").rmdir()
        (self.root / "history").symlink_to(outside_history)
        result, output = self.invoke_validator()
        self.assertEqual(result, 1)
        self.assertIn("history/ resolves outside", output)

    def test_index_file_symlink_escape_fails(self) -> None:
        self.run_validator("video-edit-history-v1")
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside_index = Path(outside_temp.name) / "INDEX.md"
        write(outside_index, "[detailed](outside.md)\n")
        index = self.root / "history" / "INDEX.md"
        index.unlink()
        index.symlink_to(outside_index)
        result, output = self.invoke_validator()
        self.assertEqual(result, 1)
        self.assertIn("history/INDEX.md resolves outside history/", output)


if __name__ == "__main__":
    unittest.main()
