from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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


def days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

def fixture_review():
    return {'sources':{source:{'platform':platform,'data_class':'non_authorized_public_metadata','basis_ref':'synthetic-test-only',
        'review_expires_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
        'metadata_storage_allowed':True,'max_storage_days':30,'max_freshness_days':7}
        for platform,source in [('youtube','youtube_data_api'),('tiktok','tiktok_embed_profile')]}}

def fixture_row(value, platform='youtube'):
    return {**value, 'platform':platform, 'source':'youtube_data_api' if platform=='youtube' else 'tiktok_embed_profile',
            'data_class':'non_authorized_public_metadata','observed_at':datetime.now(timezone.utc).isoformat()}

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
        self.retention=root/"retention.json";self.retention.write_text(json.dumps(fixture_review()))
        self.watchlist.write_text("| platform | handle |\n| --- | --- |\n| youtube | example |\n")
        self.args = argparse.Namespace(
            watchlist=self.watchlist,
            out=self.out,
            health_out=self.health_out,
            previous=None, retention_review=self.retention,
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
            platform="all", _retention_review=fixture_review(),
            failure_threshold=2,
            youtube_bot_dir="/tmp/youtubebot",
            tiktok_bot_dir="/tmp/tiktokbot",
            ig_bot_dir="",
            tiktok_collector="profile-feed",
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
        rows = [fixture_row({"id":"fixture", "url": "https://example.test/video", "views": 123456})]
        result = self.invoke(rows, health("success", succeeded=1))
        self.assertEqual(result, 0)
        self.assertEqual(
            json.loads(self.out.read_text(encoding="utf-8")),
            MODULE.eligible_observations(rows, fixture_review())[0][0],
        )
        receipt = json.loads(self.health_out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["run_status"], "success")
        self.assertTrue(receipt["promoted_to_latest"])
        self.assertTrue(Path(receipt["attempt_output"]).is_file())
        self.assertEqual(Path(receipt["attempt_output"]).read_bytes(), self.out.read_bytes())

    def test_missing_capture_and_review_cannot_rank_or_replace_latest(self):
        self.out.write_text('protected latest')
        invalid=[{'platform':'youtube','source':'youtube_data_api','data_class':'non_authorized_public_metadata','id':'undated','views':999999,'publishedAt':datetime.now(timezone.utc).isoformat()}]
        with patch.object(MODULE,'run_json',return_value=(invalid,None)):
            rows,receipt=MODULE.collect(self.collect_args('youtube'),[{'platform':'youtube','handle':'example'}],set())
        self.assertEqual(rows,[])
        self.assertEqual(receipt['youtube']['retention_exclusions'][0]['reason'],'missing_actual_observation_time')
        self.assertEqual(self.invoke(invalid,health('success',1)),1)
        self.assertEqual(self.out.read_text(),'protected latest')
        result=json.loads(self.health_out.read_text());self.assertEqual(result['run_status'],'enrichment blocked')
        self.assertEqual(Path(result['attempt_output']).read_text(),'')
        blocked_args=self.collect_args('youtube');blocked_args._retention_review={}
        with patch.object(MODULE,'run_json') as collector:
            blocked_rows,blocked_health=MODULE.collect(blocked_args,[{'platform':'youtube','handle':'example'}],set())
        collector.assert_not_called();self.assertEqual(blocked_rows,[])
        self.assertEqual(blocked_health['youtube']['status'],'enrichment blocked')
        self.args.retention_review=None
        self.assertEqual(self.invoke([fixture_row({'id':'current','views':100})],health('success',1)),1)
        self.assertEqual(self.out.read_text(),'protected latest')

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
        recovered = [fixture_row({
            "url": "https://example.test/video",
            "views": 200_000,
            "postedAt": days_ago(3),
        }, "tiktok")]
        with patch.object(
            MODULE,
            "run_json",
            side_effect=[([], "primary failed"), (recovered, None)],
        ) as primary:
            args = self.collect_args("tiktok")
            args.tiktok_collector = "web-search"
            rows, receipt = MODULE.collect(
                args,
                accounts,
                set(),
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(receipt["tiktok"]["fallbacks"][0]["status"], "success")
        self.assertEqual(receipt["tiktok"]["status"], "degraded")
        command = primary.call_args_list[0].args[0]
        self.assertIn("--enable-browser-adapter", command)
        self.assertEqual(rows[0]["collection_method"], "search_seed")

    def test_tiktok_defaults_to_direct_profile_feed(self) -> None:
        accounts = [{"platform": "tiktok", "handle": "example"}]
        recovered = [fixture_row({
            "url": "https://www.tiktok.com/@example/video/1",
            "creator": "example",
            "followers": 10_000,
            "views": 200_000,
            "postedAt": days_ago(3),
            "source": "tiktok_embed_profile",
        }, "tiktok")]
        with patch.object(MODULE, "run_json", return_value=(recovered, None)) as run:
            rows, receipt = MODULE.collect(
                self.collect_args("tiktok"),
                accounts,
                set(),
            )
        command = run.call_args.args[0]
        self.assertIn("profile-feed", command)
        self.assertNotIn("web-search", command)
        self.assertEqual(rows[0]["collection_method"], "profile")
        self.assertEqual(receipt["tiktok"]["status"], "success")


if __name__ == "__main__":
    unittest.main()


class ChannelRoutingTests(unittest.TestCase):
    def test_verified_channel_route_and_lossless_adapter(self):
        args=AccountWatchlistOutputTests.collect_args(self,"youtube")
        account={"platform":"youtube","handle":"example","channel_id":"UC1234567890123456789012"}
        source=fixture_row({"id":"abc","channelId":account["channel_id"],"url":"https://youtube.com/watch?v=abc","views":200000,
            "subscribers":1000,"durationSeconds":30,"publishedAt":datetime.now(timezone.utc).isoformat(),"baselineVideos":[{"id":"peer"}]})
        with patch.object(MODULE,"run_json",return_value=([source],None)) as run:
            rows,_=MODULE.collect(args,[account],set())
        command=run.call_args.args[0]
        self.assertIn("--channel-ref",command)
        self.assertIn(account["channel_id"],command)
        self.assertEqual(rows[0]["video_id"],"abc")
        self.assertEqual(rows[0]["duration_seconds"],30)
        self.assertEqual(rows[0]["baseline_members"],[])
        self.assertEqual(rows[0]["collection_method"],"channel_uploads")

    def test_timeout_cancels_descendant_process_group(self):
        import time
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/"unexpected"
            child="import time,pathlib; time.sleep(.25); pathlib.Path("+repr(str(marker))+").touch()"
            code="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"+repr(child)+"]); time.sleep(10)"
            rows,error=MODULE.run_json([sys.executable,'-c',code],directory,.05)
            self.assertEqual(rows,[])
            self.assertIn("cancelled",error)
            time.sleep(.3)
            self.assertFalse(marker.exists())


class AttemptRetentionTests(unittest.TestCase):
    def test_success_keeps_receipted_attempt_and_promotes_complete_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);watchlist=root/'watch.md';watchlist.write_text('| platform | handle |\n| --- | --- |\n| youtube | example |\n')
            output=root/'latest.jsonl';output.write_text('previous snapshot')
            health=root/'health.json';rows=[fixture_row({'id':'synthetic','url':'https://youtube.com/watch?v=synthetic','views':100})]
            retention=root/'retention.json';retention.write_text(json.dumps(fixture_review()))
            args=argparse.Namespace(watchlist=watchlist,out=output,health_out=health,previous=None,retention_review=retention)
            with patch.object(MODULE,'parse_args',return_value=args), patch.object(MODULE,'collect',return_value=(rows,MODULE.empty_health())):
                self.assertEqual(MODULE.main(),0)
            receipt=json.loads(health.read_text());attempt=Path(receipt['attempt_output'])
            self.assertTrue(attempt.exists())
            self.assertEqual(attempt.read_bytes(),output.read_bytes())
            self.assertEqual(json.loads(attempt.read_text())['views'],100)
            self.assertFalse(list(root.glob('.watchlist-promote-*')))
