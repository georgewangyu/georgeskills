#!/usr/bin/env python3
"""Small deterministic test suite for score_allocations.py."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from score_allocations import InputError, calculate


SKILL_DIR = Path(__file__).resolve().parents[1]
EXAMPLE = SKILL_DIR / "references" / "example-general-professional.json"


class AllocatorTests(unittest.TestCase):
    def test_example_allocates_all_capacity_within_constraints(self) -> None:
        result = calculate(json.loads(EXAMPLE.read_text(encoding="utf-8")))
        self.assertEqual(result["total_allocation_pct"], 100.0)
        self.assertEqual(len(result["results"]), 5)
        for lane in result["results"]:
            self.assertGreaterEqual(lane["allocation_pct"], lane["min_pct"])
            self.assertLessEqual(lane["allocation_pct"], lane["max_pct"])
            self.assertIn("allocation_hours", lane)

    def test_invalid_floor_total_is_rejected(self) -> None:
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        for lane in data["lanes"]:
            lane["min_pct"] = 25
        with self.assertRaises(InputError):
            calculate(data)

    def test_core_weights_must_sum_to_one(self) -> None:
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        data["model"] = {
            "core_weights": {
                "pnr": 0.20,
                "bp": 0.20,
                "ca": 0.20,
                "fit": 0.20,
                "align": 0.10
            },
            "confidence_floor": 0.60,
            "penalties": {"oc": 0.12, "sat": 0.12}
        }
        with self.assertRaises(InputError):
            calculate(data)

    def test_cap_redistributes_remaining_capacity(self) -> None:
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        data["lanes"][0]["max_pct"] = 30
        result = calculate(data)
        career = next(
            lane for lane in result["results"] if lane["name"] == "Salaried career"
        )
        self.assertEqual(career["allocation_pct"], 30.0)
        self.assertEqual(result["total_allocation_pct"], 100.0)

    def test_all_zero_scores_use_bounded_fallback(self) -> None:
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        for lane in data["lanes"]:
            lane["scores"] = {key: 0 for key in lane["scores"]}
        result = calculate(data)
        self.assertEqual(result["total_allocation_pct"], 100.0)
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
