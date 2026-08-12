from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "score_video_breakouts.py"
SPEC = importlib.util.spec_from_file_location("score_video_breakouts", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FollowerConversionTests(unittest.TestCase):
    def test_conversion_ratios_and_cta_mode(self) -> None:
        candidate = MODULE.build_candidates(
            [
                {
                    "platform": "instagram",
                    "creator_handle": "examplecreator",
                    "followers": 10_000,
                    "views": 500_000,
                    "reach": 400_000,
                    "follows": 5_000,
                    "saves": 4_000,
                    "shares": 2_000,
                    "duration_seconds": 60,
                    "avg_watch_seconds": 30,
                    "profile_continuity": "high",
                    "series_open_loop": "medium",
                    "topic_profile_fit": 0.8,
                    "cta_type": "follow_gated_asset",
                    "attribution": "creator_first_party",
                }
            ]
        )[0]

        self.assertAlmostEqual(candidate.follows_per_view, 0.01)
        self.assertAlmostEqual(candidate.follows_per_reach, 0.0125)
        self.assertAlmostEqual(candidate.avg_watch_percentage, 0.5)
        self.assertAlmostEqual(candidate.saves_per_view, 0.008)
        self.assertAlmostEqual(candidate.shares_per_view, 0.004)
        self.assertEqual(MODULE.conversion_mode(candidate.cta_type), "funnel-contaminated")
        self.assertAlmostEqual(candidate.attribution_confidence, 0.75)

    def test_missing_follow_data_does_not_create_conversion_candidate(self) -> None:
        candidates = MODULE.build_candidates(
            [{"platform": "youtube", "creator_handle": "sample", "followers": 100, "views": 10_000}]
        )

        self.assertEqual(candidates[0].conversion_score, 0.0)
        self.assertEqual([row for row in candidates if row.follows > 0], [])

    def test_current_followers_are_not_used_as_attributed_follows(self) -> None:
        candidate = MODULE.build_candidates(
            [{"platform": "instagram", "creator_handle": "sample", "followers": 900_000, "views": 2_000_000}]
        )[0]

        self.assertEqual(candidate.follows, 0.0)
        self.assertEqual(candidate.follows_per_view, 0.0)


if __name__ == "__main__":
    unittest.main()
