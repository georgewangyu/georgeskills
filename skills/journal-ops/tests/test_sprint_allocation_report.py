from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sprint_allocation_report as report  # noqa: E402


class SprintAllocationReportTests(unittest.TestCase):
    def test_each_top_level_bullet_becomes_an_activity_record(self) -> None:
        section = """
- Interview block: completed the Datadog interview.
  - Nested supporting detail should remain part of the interview block.
- Content block: edited and posted one video.
- Work block: handled an on-call issue.
"""

        sessions = report.parse_sprints_section(section, date(2026, 7, 1))

        self.assertEqual(3, len(sessions))
        self.assertEqual(
            ["Career/Interview", "Content", "Day Job"],
            [session.domain for session in sessions],
        )
        self.assertEqual("Interview block", sessions[0].title)
        self.assertIn("completed the Datadog interview", sessions[0].body)

    def test_explicit_tags_override_incidental_body_keywords(self) -> None:
        section = """
- [work] Improved an internal video-processing pipeline.
- [health] Watched an exercise video before a wrist-safe gym session.
- [product] Fixed a public video page in the product.
"""

        sessions = report.parse_sprints_section(section, date(2026, 7, 8))

        self.assertEqual(
            ["Day Job", "Personal", "Personal Project"],
            [session.domain for session in sessions],
        )

    def test_unlabeled_activity_does_not_become_fake_deep_work(self) -> None:
        section = """
- Product cleanup: fixed metadata and release configuration.
- Video editing (deep, multi-block): completed a locked visual pass.
"""

        sessions = report.parse_sprints_section(section, date(2026, 7, 12))

        self.assertEqual("unclassified", sessions[0].intensity)
        self.assertEqual(0.0, sessions[0].focus_hours)
        self.assertEqual("deep", sessions[1].intensity)
        self.assertEqual(1.5, sessions[1].focus_hours)


if __name__ == "__main__":
    unittest.main()
