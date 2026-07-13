import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "normalize_final_videos.py"
SPEC = importlib.util.spec_from_file_location("normalize_final_videos", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class NormalizeFinalVideosTest(unittest.TestCase):
    def test_central_final_storage_does_not_require_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = MODULE.plan_item(
                {
                    "source": "export.mp4",
                    "canonical_name": "2026-07-12_example_final_v01.mp4",
                },
                root / "incoming",
                None,
                root / "by-week" / "2026-W28_video-batch",
                root / "index",
                "final-videos",
            )

            self.assertEqual(
                paths["final"],
                root
                / "by-week"
                / "2026-W28_video-batch"
                / "2026-07-12_example_final_v01.mp4",
            )
            self.assertEqual(
                paths["index"], root / "index" / "2026-07-12_example_final_v01.mp4"
            )

    def test_legacy_project_storage_still_works(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = MODULE.plan_item(
                {"source": "export.mp4", "project": "2026-07-12_example"},
                root / "incoming",
                root / "batch",
                None,
                root / "index",
                "final-videos",
            )

            self.assertEqual(
                paths["final"],
                root
                / "batch"
                / "2026-07-12_example"
                / "final-videos"
                / "2026-07-12_example_final_v01.mp4",
            )


if __name__ == "__main__":
    unittest.main()
