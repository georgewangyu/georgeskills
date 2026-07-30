from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "resume_page_utilization.py"
)
SPEC = importlib.util.spec_from_file_location("resume_page_utilization", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ResumePageUtilizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.pdf = Path(self.temp.name) / "resume.pdf"
        self.pdf.write_bytes(b"%PDF-fixture")
        self.args = argparse.Namespace(
            pdf=self.pdf,
            dpi=100,
            white_threshold=245,
            min_content_height_pct=80.0,
            max_bottom_whitespace_in=1.25,
            min_bottom_whitespace_in=0.35,
            min_side_whitespace_in=0.4,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def metrics(
        self,
        *,
        content_height_pct: float = 90.0,
        bottom_px: int = 900,
    ) -> dict[str, float]:
        return {
            "width_px": 800,
            "height_px": 1000,
            "top_px": 40,
            "bottom_px": bottom_px,
            "left_px": 50,
            "right_px": 749,
            "content_height_pct": content_height_pct,
            "content_width_pct": 87.5,
            "ink_density_pct": 8.0,
        }

    def evaluate_with(
        self,
        pages: int,
        metrics: dict[str, float],
    ) -> dict[str, object]:
        with (
            patch.object(MODULE, "pdf_page_count", return_value=pages),
            patch.object(
                MODULE,
                "render_first_page",
                return_value=Path(self.temp.name) / "page.pgm",
            ),
            patch.object(MODULE, "content_bounds", return_value=metrics),
        ):
            return MODULE.evaluate(self.args)

    def test_missing_pdf_fails(self) -> None:
        self.args.pdf = Path(self.temp.name) / "missing.pdf"
        with self.assertRaises(FileNotFoundError):
            MODULE.evaluate(self.args)

    def test_missing_render_tool_fails(self) -> None:
        with patch.object(MODULE.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "pdftoppm is required"):
                MODULE.render_first_page(
                    self.pdf,
                    Path(self.temp.name) / "page",
                    100,
                )

    def test_malformed_pgm_fails(self) -> None:
        malformed = Path(self.temp.name) / "malformed.pgm"
        malformed.write_bytes(b"P2\n1 1\n255\n0\n")
        with self.assertRaisesRegex(RuntimeError, "binary grayscale"):
            MODULE.read_pgm(malformed)

    def test_multipage_pdf_fails(self) -> None:
        report = self.evaluate_with(2, self.metrics())
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("expected exactly one page", report["failures"][0])

    def test_underfilled_page_fails(self) -> None:
        report = self.evaluate_with(
            1,
            self.metrics(content_height_pct=70.0),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("underfilled page" in item for item in report["failures"])
        )

    def test_crowded_bottom_edge_fails(self) -> None:
        report = self.evaluate_with(1, self.metrics(bottom_px=980))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("crowded bottom edge" in item for item in report["failures"])
        )

    def test_pdfinfo_failure_propagates(self) -> None:
        with patch.object(
            MODULE.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(1, ["pdfinfo"]),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                MODULE.pdf_page_count(self.pdf)


if __name__ == "__main__":
    unittest.main()
