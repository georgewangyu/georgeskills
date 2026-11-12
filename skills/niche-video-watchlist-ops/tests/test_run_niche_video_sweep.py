import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/"scripts/run_niche_video_sweep.py"
spec=importlib.util.spec_from_file_location("niche",SCRIPT)
niche=importlib.util.module_from_spec(spec);spec.loader.exec_module(niche)

class NicheTests(unittest.TestCase):
    def settings(self, platform="all", watchlist=None):
        with patch.object(sys,"argv",[str(SCRIPT),"--out","/tmp/test-niche.jsonl","--platform",platform]):
            args=niche.parse_args()
        settings = niche.merge_args(args,{"lanes":["a topic"],"bot_dirs":{"youtube":"yt","tiktok":"tt","instagram":"ig"},"watchlist":watchlist or []})
        settings['retention_review'] = {'sources':{source:{'platform':platform,
            'data_class':'non_authorized_public_metadata','basis_ref':'synthetic-only',
            'review_expires_at':'2099-01-01T00:00:00Z','metadata_collection_allowed':True,
            'metadata_storage_allowed':True,'derived_metrics_allowed':True,
            'max_storage_days':30,'max_freshness_days':7}
            for platform,source in [('youtube','youtube_data_api'),('instagram','instagram_private_api'),('tiktok','tiktok_embed_profile')]}}
        return settings

    def test_defaults_and_no_handle_keyword_seeding(self):
        with patch.object(sys,"argv",[str(SCRIPT),"--out","/tmp/test-niche.jsonl"]):
            args=niche.parse_args()
        self.assertEqual(args.platform,"youtube")
        settings=niche.merge_args(args,{"lanes":["topic"],"watchlist":[{"platform":"youtube","handle":"Creator Name"}]})
        self.assertEqual(settings["lanes"],["topic"])

    def test_permitted_commands_and_metadata_preserved(self):
        settings=self.settings(watchlist=[{"platform":"youtube","handle":"label","channel_id":"UCexact"},{"platform":"tiktok","handle":"example"}])
        raw={"id":"v","channelId":"UCexact","durationSeconds":30,"thumbnail":"thumb","views":0,"likes":0,"comments":None,"publishedAt":"2026-10-01T00:00:00Z","baselineVideos":[{"id":"peer"}],"baselineViews":10,"url":"https://youtube.com/watch?v=v"}
        captured = datetime.now(timezone.utc).isoformat()
        def output(command, *_):
            platform = 'youtube' if 'find' in command else 'tiktok' if 'profile-feed' in command else 'instagram'
            source = {'youtube':'youtube_data_api','tiktok':'tiktok_embed_profile','instagram':'instagram_private_api'}[platform]
            return ([{**raw,'platform':platform,'source':source,'data_class':'non_authorized_public_metadata','observed_at':captured}], None)
        with patch.object(niche,"bounded_run_json",side_effect=output) as run:
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
        self.assertEqual(row["baseline_members"],[])
        self.assertIsNone(row["baseline_views"])
        self.assertEqual(row["metrics"]["likes"],0)
        self.assertIsNone(row["metrics"]["comments"])
        self.assertEqual(row["observed_at"],captured)

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

    def test_missing_review_blocks_before_collection(self):
        settings = self.settings('youtube')
        settings['retention_review'] = {}
        with patch.object(niche, 'bounded_run_json') as run:
            self.assertEqual(niche.collect(settings), [])
        run.assert_not_called()

    def test_undated_rows_are_excluded_without_fabricated_time(self):
        settings = self.settings('youtube')
        raw = {'platform':'youtube','source':'youtube_data_api','data_class':'non_authorized_public_metadata','id':'v'}
        with patch.object(niche, 'bounded_run_json', return_value=([raw], None)):
            self.assertEqual(niche.collect(settings), [])
        self.assertEqual(settings['health']['youtube']['retention_exclusions'][0]['reason'], 'missing_actual_observation_time')

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/"saved.jsonl";output.write_text("good snapshot")
            with patch.object(sys,"argv",[str(SCRIPT),"--lane","topic","--out",str(output)]):
                with self.assertRaises(FileExistsError):niche.main()
            self.assertEqual(output.read_text(),"good snapshot")

if __name__=="__main__":unittest.main()
