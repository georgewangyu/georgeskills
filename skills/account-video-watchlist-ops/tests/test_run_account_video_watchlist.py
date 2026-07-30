from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_account_video_watchlist.py"
)
SPEC = importlib.util.spec_from_file_location("run_account_video_watchlist", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def health(status: str, succeeded: int = 0) -> dict[str, dict[str, object]]:
    result = MODULE.empty_health()
    result["youtube"]["status"] = status
    result["youtube"]["attempted"] = 1
    result["youtube"]["succeeded"] = succeeded
    result["youtube"]["failed"] = 0 if succeeded else 1
    return result


class AccountWatchlistOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.out = root / "latest.jsonl"
        self.health_out = root / "health.json"
        self.watchlist = root / "watchlist.md"
        self.watchlist.write_text("| platform | handle |\n| --- | --- |\n| youtube | example |\n")
        self.args = argparse.Namespace(
            watchlist=self.watchlist,
            out=self.out,
            health_out=self.health_out,
            previous=None,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invoke(
        self,
        rows: list[dict[str, object]],
        collector_health: dict[str, dict[str, object]],
    ) -> int:
        with (
            patch.object(MODULE, "parse_args", return_value=self.args),
            patch.object(MODULE, "collect", return_value=(rows, collector_health)),
        ):
            return MODULE.main()

    def collect_args(self, platform: str) -> argparse.Namespace:
        return argparse.Namespace(
            platform="all",
            failure_threshold=2,
            youtube_bot_dir="/tmp/youtubebot",
            tiktok_bot_dir="/tmp/tiktokbot",
            ig_bot_dir="",
            max_age_days=45,
            max_base=10_000_000,
            min_views=100_000,
            limit_per_account=10,
            timeout_seconds=60,
            tiktok_web_backend="auto",
            tiktok_web_browser="chromium",
            tiktok_web_headless="true",
            tiktok_web_mute_audio="true",
            tiktok_node_fallback="true",
        )

    def test_unavailable_run_preserves_known_good_latest(self) -> None:
        self.out.write_text('{"url":"known-good"}\n', encoding="utf-8")
        result = self.invoke([], health("unavailable"))
        self.assertEqual(result, 1)
        self.assertEqual(
            self.out.read_text(encoding="utf-8"),
            '{"url":"known-good"}\n',
        )
        receipt = json.loads(self.health_out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["run_status"], "unavailable")
        self.assertFalse(receipt["promoted_to_latest"])
        self.assertTrue(receipt["previous_output_preserved"])
        self.assertTrue(Path(receipt["attempt_output"]).is_file())

    def test_empty_success_preserves_known_good_latest(self) -> None:
        self.out.write_text('{"url":"known-good"}\n', encoding="utf-8")
        result = self.invoke([], health("success", succeeded=1))
        self.assertEqual(result, 1)
        self.assertEqual(
            self.out.read_text(encoding="utf-8"),
            '{"url":"known-good"}\n',
        )
        receipt = json.loads(self.health_out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["run_status"], "empty")
        self.assertFalse(receipt["promoted_to_latest"])

    def test_usable_rows_atomically_promote_latest(self) -> None:
        rows = [{"url": "https://example.test/video", "views": 123456}]
        result = self.invoke(rows, health("success", succeeded=1))
        self.assertEqual(result, 0)
        self.assertEqual(
            json.loads(self.out.read_text(encoding="utf-8")),
            rows[0],
        )
        receipt = json.loads(self.health_out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["run_status"], "success")
        self.assertTrue(receipt["promoted_to_latest"])
        self.assertFalse(Path(receipt["attempt_output"]).exists())

    def test_platform_circuit_breaker_skips_remaining_accounts(self) -> None:
        accounts = [
            {"platform": "youtube", "handle": f"creator-{index}"}
            for index in range(3)
        ]
        with patch.object(
            MODULE,
            "run_json",
            return_value=([], "collector unavailable"),
        ):
            rows, receipt = MODULE.collect(
                self.collect_args("youtube"),
                accounts,
                set(),
            )
        self.assertEqual(rows, [])
        self.assertEqual(receipt["youtube"]["attempted"], 2)
        self.assertEqual(
            receipt["youtube"]["skipped_after_circuit_breaker"],
            1,
        )
        self.assertEqual(receipt["youtube"]["status"], "unavailable")

    def test_tiktok_node_fallback_recovers_one_account(self) -> None:
        accounts = [{"platform": "tiktok", "handle": "example"}]
        recovered = [{
            "url": "https://example.test/video",
            "views": 200_000,
            "postedAt": "2026-07-29T00:00:00Z",
        }]
        with patch.object(
            MODULE,
            "run_json",
            side_effect=[([], "primary failed"), (recovered, None)],
        ):
            rows, receipt = MODULE.collect(
                self.collect_args("tiktok"),
                accounts,
                set(),
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(receipt["tiktok"]["fallbacks"][0]["status"], "success")
        self.assertEqual(receipt["tiktok"]["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
