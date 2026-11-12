import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/"scripts/run_niche_video_sweep.py"
spec=importlib.util.spec_from_file_location("niche",SCRIPT)
niche=importlib.util.module_from_spec(spec);spec.loader.exec_module(niche)

class NicheTests(unittest.TestCase):
    def settings(self, platform="all", watchlist=None):
        with patch.object(sys,"argv",[str(SCRIPT),"--out","/tmp/test-niche.jsonl","--platform",platform]):
            args=niche.parse_args()
        return niche.merge_args(args,{"lanes":["a topic"],"bot_dirs":{"youtube":"yt","tiktok":"tt","instagram":"ig"},"watchlist":watchlist or []})

    def test_defaults_and_no_handle_keyword_seeding(self):
        with patch.object(sys,"argv",[str(SCRIPT),"--out","/tmp/test-niche.jsonl"]):
            args=niche.parse_args()
        self.assertEqual(args.platform,"youtube")
        settings=niche.merge_args(args,{"lanes":["topic"],"watchlist":[{"platform":"youtube","handle":"Creator Name"}]})
        self.assertEqual(settings["lanes"],["topic"])

    def test_permitted_commands_and_metadata_preserved(self):
        settings=self.settings(watchlist=[{"platform":"youtube","handle":"label","channel_id":"UCexact"},{"platform":"tiktok","handle":"example"}])
        raw={"id":"v","channelId":"UCexact","durationSeconds":30,"thumbnail":"thumb","views":0,"likes":0,"comments":None,"publishedAt":"2026-10-01T00:00:00Z","baselineVideos":[{"id":"peer"}],"baselineViews":10,"url":"https://youtube.com/watch?v=v"}
        with patch.object(niche,"bounded_run_json",return_value=([raw],None)) as run:
            rows=niche.collect(settings)
        commands=[c.args[0] for c in run.call_args_list]
        self.assertTrue(any("--channel-ref" in c and "UCexact" in c for c in commands))
        self.assertTrue(any("profile-feed" in c for c in commands))
        self.assertFalse(any("web-search" in c for c in commands))
        self.assertTrue(all(c.args[2]==45 for c in run.call_args_list))
        row=next(r for r in rows if r["platform"]=="youtube")
        self.assertEqual(row["creator_id"],"UCexact")
        self.assertEqual(row["duration_seconds"],30)
        self.assertEqual(row["thumbnail"],"thumb")
        self.assertEqual(row["baseline_members"],[{"id":"peer"}])
        self.assertEqual(row["metrics"]["likes"],0)
        self.assertIsNone(row["metrics"]["comments"])
        self.assertIsNotNone(row["observed_at"])

    def test_tiktok_keywords_never_launch_browser(self):
        settings=self.settings("tiktok")
        with patch.object(niche,"bounded_run_json") as run:
            self.assertEqual(niche.collect(settings),[])
        run.assert_not_called()
        self.assertEqual(settings["health"]["tiktok"]["status"],"not_attempted")

    def test_failure_circuit_breaker(self):
        settings=self.settings("tiktok",[{"platform":"tiktok","handle":str(i)} for i in range(5)])
        with patch.object(niche,"bounded_run_json",return_value=([],"collector timeout")) as run:
            self.assertEqual(niche.collect(settings),[])
        self.assertEqual(run.call_count,2)
        self.assertEqual(settings["health"]["tiktok"]["skipped_after_circuit_breaker"],3)
        self.assertEqual(settings["health"]["tiktok"]["status"],"unavailable")

    def test_empty_collector_is_degraded(self):
        settings=self.settings("youtube")
        with patch.object(niche,"bounded_run_json",return_value=([],None)):
            self.assertEqual(niche.collect(settings),[])
        self.assertEqual(settings['health']['youtube']['status'],'degraded')

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/"saved.jsonl";output.write_text("good snapshot")
            with patch.object(sys,"argv",[str(SCRIPT),"--lane","topic","--out",str(output)]):
                with self.assertRaises(FileExistsError):niche.main()
            self.assertEqual(output.read_text(),"good snapshot")

if __name__=="__main__":unittest.main()
