from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "scaffold_manim_project.py"


class ScaffoldManimProjectTests(unittest.TestCase):
    def test_scaffolds_replaced_and_parseable_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "gradient-descent"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--project-name",
                    "Gradient Descent",
                    "--scene-class",
                    "GradientDescentExplainer",
                    "--title",
                    "Why the loss falls",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("Created 5 files", result.stdout)
            self.assertIn('name = "gradient-descent"', (output / "pyproject.toml").read_text())
            scene = (output / "scene.py").read_text()
            self.assertIn("class GradientDescentExplainer", scene)
            self.assertIn('SCENE_TITLE = "Why the loss falls"', scene)
            self.assertNotIn("__SCENE_CLASS__", scene)
            py_compile.compile(str(output / "scene.py"), doraise=True)

            handoff = json.loads((output / "MANIM_HANDOFF.json").read_text())
            self.assertEqual("GradientDescentExplainer", handoff["scene_class"])
            self.assertEqual(1080, handoff["render"]["width"])

    def test_refuses_non_empty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "existing"
            output.mkdir()
            (output / "keep.txt").write_text("preserve me")
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
            self.assertEqual("preserve me", (output / "keep.txt").read_text())


if __name__ == "__main__":
    unittest.main()
