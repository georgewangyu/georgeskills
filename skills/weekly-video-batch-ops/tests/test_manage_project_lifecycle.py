from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "manage_project_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("manage_project_lifecycle", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
lifecycle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lifecycle)


class ManageProjectLifecycleTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, Path]:
        media = root / "media"
        previous = media / "batches" / "2026" / "2026-W28_video-batch"
        current = media / "batches" / "2026" / "2026-W29_video-batch"
        previous.mkdir(parents=True)
        current.mkdir(parents=True)
        return media, previous, current

    def test_dropped_status_is_machine_readable_and_not_carried(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media, previous, current = self.fixture(Path(temporary))
            project = previous / "2026-07-10_dropped-video"
            project.mkdir()

            lifecycle.write_status(project, "dropped", "Creator passed.", True)
            output = lifecycle.refresh_views(media, current, 8, True)

            manifest = json.loads((project / lifecycle.STATUS_FILE).read_text())
            self.assertEqual(manifest["status"], "dropped")
            self.assertFalse(manifest["carryover_eligible"])
            self.assertFalse((current / "_CARRYOVER" / project.name).exists())
            self.assertIn(str(project.resolve()), output["dropped_projects"])

    def test_active_prior_project_appears_as_carryover_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media, previous, current = self.fixture(Path(temporary))
            project = previous / "2026-07-10_active-video"
            project.mkdir()
            lifecycle.write_status(project, "active", None, True)

            lifecycle.refresh_views(media, current, 8, True)

            link = current / "_CARRYOVER" / project.name
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), project.resolve())

    def test_completed_project_appears_in_origin_completed_view(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media, previous, current = self.fixture(Path(temporary))
            project = previous / "2026-07-10_finished-video"
            project.mkdir()

            lifecycle.write_status(project, "completed", None, True)
            lifecycle.refresh_views(media, current, 8, True)

            completed = previous / "_COMPLETED" / project.name
            self.assertTrue(completed.is_symlink())
            self.assertEqual(completed.resolve(), project.resolve())
            self.assertFalse((current / "_CARRYOVER" / project.name).exists())

    def test_dry_run_does_not_write_or_create_views(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media, previous, current = self.fixture(Path(temporary))
            project = previous / "2026-07-10_active-video"
            project.mkdir()

            lifecycle.write_status(project, "active", None, False)
            lifecycle.refresh_views(media, current, 8, False)

            self.assertFalse((project / lifecycle.STATUS_FILE).exists())
            self.assertFalse((current / "_CARRYOVER").exists())
            self.assertFalse((current / "_COMPLETED").exists())


if __name__ == "__main__":
    unittest.main()
