from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "scaffold_editorial_motion_project.py"


class ScaffoldEditorialMotionProjectTests(unittest.TestCase):
    def test_scaffolds_configured_project_without_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "queue-to-controller"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--project-name",
                    "Queue to Controller",
                    "--title",
                    "One control layer",
                    "--duration-seconds",
                    "3.5",
                    "--fps",
                    "24",
                    "--width",
                    "720",
                    "--height",
                    "1280",
                    "--delivery-mode",
                    "full-screen",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("Created 7 files", result.stdout)
            package = json.loads((output / "package.json").read_text())
            self.assertEqual("queue-to-controller", package["name"])
            self.assertIn("--image-format=png", package["scripts"]["render:alpha"])
            self.assertIn("--muted", package["scripts"]["render:review"])
            self.assertEqual("4.0.332", package["dependencies"]["@remotion/google-fonts"])

            handoff = json.loads((output / "MOTION_HANDOFF.json").read_text())
            self.assertEqual("full-screen", handoff["delivery"]["mode"])
            self.assertEqual(84, round(handoff["delivery"]["duration_seconds"] * 24))
            self.assertEqual(720, handoff["delivery"]["width"])
            self.assertEqual("outputs/review.mp4", handoff["artifacts"]["final_clip"])
            self.assertEqual("npm run render:review", handoff["source"]["render_command"])

            spec = (output / "src" / "motionSpec.ts").read_text()
            self.assertIn("durationInFrames: 84", spec)
            self.assertIn('title: "One control layer"', spec)
            self.assertIn("firstHoldEndFrame:", spec)
            self.assertIn("cardStaggerFrames:", spec)

            for path in output.rglob("*"):
                if path.is_file():
                    self.assertNotRegex(path.read_text(), r"__[A-Z][A-Z0-9_]+__")

    def test_refuses_non_empty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "existing"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("preserve me")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--project-name",
                    "example",
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("non-empty directory", result.stderr)
            self.assertEqual("preserve me", marker.read_text())

    def test_rejects_out_of_range_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(Path(temp_dir) / "invalid"),
                    "--project-name",
                    "example",
                    "--duration-seconds",
                    "0.5",
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("duration must be between", result.stderr)

    def test_quantizes_duration_to_whole_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "quantized"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--project-name",
                    "quantized",
                    "--duration-seconds",
                    "1.05",
                    "--fps",
                    "30",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            handoff = json.loads((output / "MOTION_HANDOFF.json").read_text())
            self.assertEqual(32, round(handoff["delivery"]["duration_seconds"] * 30))
            self.assertAlmostEqual(32 / 30, handoff["delivery"]["duration_seconds"])
            spec = (output / "src" / "motionSpec.ts").read_text()
            self.assertIn("durationInFrames: 32", spec)
            self.assertIn("durationInSeconds: 1.0666666666666667", spec)

    def test_rejects_blank_or_oversized_title(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for title, message in (("   ", "must not be empty"), ("x" * 73, "72 characters")):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--output",
                        str(Path(temp_dir) / f"invalid-{len(title)}"),
                        "--project-name",
                        "example",
                        "--title",
                        title,
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn(message, result.stderr)

    def test_rejects_unadapted_aspect_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(Path(temp_dir) / "landscape"),
                    "--project-name",
                    "example",
                    "--width",
                    "1920",
                    "--height",
                    "1080",
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("9:16 design space", result.stderr)


if __name__ == "__main__":
    unittest.main()
