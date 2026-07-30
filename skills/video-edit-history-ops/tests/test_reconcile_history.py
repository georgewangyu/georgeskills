from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "reconcile_history.py"
)
SPEC = importlib.util.spec_from_file_location("reconcile_history", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ReconcileHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.history = root / "history-root"
        self.projects = root / "projects"
        self.project = self.projects / "example-video"
        self.record = (
            self.history
            / "history"
            / "2026"
            / "2026-07-27_example-video.md"
        )
        write(
            self.record,
            "---\n"
            "schema: video-edit-history-v1\n"
            "video_id: 2026-07-27_example-video\n"
            "---\n",
        )
        write(
            self.history / "history" / "INDEX.md",
            "[detailed](2026/2026-07-27_example-video.md)\n",
        )
        write(
            self.project / "REEL_BRIEF.md",
            "Status: ready for creator review\n",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_pointer(
        self,
        video_id: str = "2026-07-27_example-video",
        history_record: str = "history/2026/2026-07-27_example-video.md",
    ) -> None:
        write(
            self.project / "AI_EDIT_HISTORY.md",
            "---\n"
            "schema: ai-edit-history-pointer-v1\n"
            f"video_id: {video_id}\n"
            f"history_record: {history_record}\n"
            "capture_stage: reviewable\n"
            "captured_at: 2026-07-27\n"
            "---\n",
        )

    def test_complete_project_passes(self) -> None:
        self.add_pointer()
        projects, issues = MODULE.run_audit(
            self.history, [self.projects]
        )
        self.assertEqual(projects, [self.project.resolve()])
        self.assertEqual(issues, [])

    def test_reviewable_project_without_pointer_is_reported(self) -> None:
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual([issue.code for issue in issues], ["MISSING_POINTER"])

    def test_video_id_mismatch_is_reported(self) -> None:
        self.add_pointer("2026-07-27_wrong-video")
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual(
            [issue.code for issue in issues], ["VIDEO_ID_MISMATCH"]
        )

    def test_orphan_record_is_reported(self) -> None:
        self.add_pointer()
        write(self.history / "history" / "INDEX.md", "# Empty\n")
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual(
            sorted(issue.code for issue in issues),
            ["MISSING_INDEX_LINK", "ORPHAN_RECORD"],
        )

    def test_plain_text_path_is_not_treated_as_an_index_link(self) -> None:
        self.add_pointer()
        write(
            self.history / "history" / "INDEX.md",
            "Needs linking: 2026/2026-07-27_example-video.md\n",
        )
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual(
            sorted(issue.code for issue in issues),
            ["MISSING_INDEX_LINK", "ORPHAN_RECORD"],
        )

    def test_prefix_collision_is_not_treated_as_an_index_link(self) -> None:
        self.add_pointer()
        write(
            self.history / "history" / "INDEX.md",
            "[different](2026/2026-07-27_example-video.md.bak)\n",
        )
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual(
            sorted(issue.code for issue in issues),
            ["MISSING_INDEX_LINK", "ORPHAN_RECORD"],
        )

    def test_absolute_record_pointer_is_rejected(self) -> None:
        self.add_pointer(history_record=self.record.as_posix())
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual([issue.code for issue in issues], ["INVALID_POINTER"])

    def test_traversal_record_pointer_is_rejected(self) -> None:
        self.add_pointer(history_record="../outside.md")
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual([issue.code for issue in issues], ["INVALID_POINTER"])

    def test_symlink_escape_record_pointer_is_rejected(self) -> None:
        outside = Path(self.temp.name) / "outside.md"
        write(outside, "---\nvideo_id: 2026-07-27_example-video\n---\n")
        link = self.history / "history" / "outside-link.md"
        link.symlink_to(outside)
        self.add_pointer(history_record="history/outside-link.md")
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual([issue.code for issue in issues], ["INVALID_POINTER"])

    def test_pointer_file_symlink_escape_is_rejected(self) -> None:
        self.add_pointer()
        pointer = self.project / "AI_EDIT_HISTORY.md"
        outside = Path(self.temp.name) / "outside-pointer.md"
        write(outside, pointer.read_text(encoding="utf-8"))
        pointer.unlink()
        pointer.symlink_to(outside)
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual([issue.code for issue in issues], ["INVALID_POINTER"])

    def test_detailed_record_symlink_escape_is_rejected(self) -> None:
        self.add_pointer()
        outside = Path(self.temp.name) / "outside-record.md"
        write(outside, self.record.read_text(encoding="utf-8"))
        self.record.unlink()
        self.record.symlink_to(outside)
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual(
            sorted(issue.code for issue in issues),
            ["INVALID_POINTER", "INVALID_RECORD"],
        )

    def test_history_directory_symlink_escape_is_rejected(self) -> None:
        unsafe_root = Path(self.temp.name) / "unsafe-history-root"
        outside_history = Path(self.temp.name) / "outside-history"
        write(outside_history / "INDEX.md", "# Index\n")
        unsafe_root.mkdir()
        (unsafe_root / "history").symlink_to(outside_history)
        _, issues = MODULE.run_audit(unsafe_root, [self.projects])
        self.assertEqual(
            [issue.code for issue in issues], ["INVALID_HISTORY_ROOT"]
        )

    def test_index_file_symlink_escape_is_rejected(self) -> None:
        outside_index = Path(self.temp.name) / "outside-index.md"
        write(outside_index, "[detailed](missing.md)\n")
        index = self.history / "history" / "INDEX.md"
        index.unlink()
        index.symlink_to(outside_index)
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual([issue.code for issue in issues], ["INVALID_INDEX"])

    def test_rendered_artifact_without_pointer_is_discovered(self) -> None:
        self.project.joinpath("REEL_BRIEF.md").unlink()
        write(self.project / "working" / "review.mp4", "placeholder")
        _, issues = MODULE.run_audit(self.history, [self.projects])
        self.assertEqual([issue.code for issue in issues], ["MISSING_POINTER"])


if __name__ == "__main__":
    unittest.main()
