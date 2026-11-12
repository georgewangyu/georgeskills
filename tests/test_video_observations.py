import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('video_observations', ROOT/'scripts/video_observations.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def row(views, at='2026-10-10T10:00:00Z', **extra):
    return v.observation({'platform':'youtube','id':'abc','url':'https://www.youtube.com/watch?v=abc&feature=share',
        'channelId':'creator','publishedAt':'2026-10-08T10:00:00Z','views':views,'observed_at':at, **extra})


class Observations(unittest.TestCase):
    def test_lossless_zero_missing_and_identity(self):
        result=row(0, likes=0, durationSeconds=30, thumbnail='image', baselineVideos=[{'id':'peer'}])
        self.assertEqual(result['canonical_url'], 'https://www.youtube.com/watch?v=abc')
        self.assertEqual(result['metrics']['likes'], 0)
        self.assertIsNone(result['metrics']['shares'])
        self.assertEqual(result['duration_seconds'],30)
        self.assertEqual(result['baseline_members'],[{'id':'peer'}])
        self.assertEqual(v.observation(result)['metrics'],result['metrics'])
        self.assertIsNone(v.observation({'views':20})['observed_at'])

    def test_secrets_refused(self):
        for payload in [{'accessToken':'x'}, {'nested':{'cookies':'x'}}, {'url':'https://x.test/?token=x'}]:
            with self.assertRaises(ValueError): v.observation(payload)

    def test_growth_real_timestamps(self):
        past=[row(100,'2026-10-10T06:00:00Z'),row(200,'2026-10-10T08:00:00Z')]
        growth=v.momentum(row(500),past)
        self.assertEqual(growth['views_per_hour'],150)
        self.assertEqual(growth['acceleration_per_hour'],50)
        self.assertEqual(v.momentum(row(500),[])['status'],'unavailable')
        self.assertEqual(v.momentum(row(50),past)['status'],'counter_reset')
        self.assertEqual(v.momentum(row(500),[row(400)])['status'],'unavailable')

    def test_series_and_season(self):
        a=v.series(row(5, hook_text='Season 1 Day 2/7 Learning skating'))
        b=v.series(row(5, hook_text='Season 1 Day 3/7 Learning skating'))
        self.assertEqual(a['series_id'],b['series_id'])
        self.assertEqual(a['status'],'candidate')
        self.assertEqual(a['season'],1)
        self.assertEqual(a['episode'],2)
        self.assertEqual(a['planned_episodes'],7)
        self.assertEqual(v.series(row(5,series_id='unreviewed'))['status'],'candidate')
        approved=v.annotate([row(5)],[{'platform':'youtube','video_id':'abc','series_id':'approved'}])[0]
        self.assertEqual(v.series(approved)['status'],'explicit')

    def test_rejection_and_owned_link(self):
        event={'candidate_id':'abc','platform':'youtube','decision_id':'d','decided_at':'2026-10-10T10:00:00Z','state':'rejected','reason':'not filmable'}
        result=row(500)
        result['feedback']=v.feedback_links(result,[event])
        self.assertEqual(v.diverse_shortlist([result]),[])
        with self.assertRaises(ValueError): v.feedback_links(result,[{**event,'reason':None}])
        with self.assertRaises(ValueError): v.feedback_links(result,[{**event,'owned_result':{'views':500}}])

    def test_diversity_and_rights(self):
        rows=[row(100,id=str(i),channelId=str(i),exploration_lane=lane) for i,lane in enumerate(['niche','niche','adjacent','wildcard'])]
        self.assertEqual([r['exploration_lane'] for r in v.diverse_shortlist(rows,3)],['niche','adjacent','wildcard'])
        self.assertTrue(v.policy_status(rows[0],{}).startswith('blocked'))
        self.assertTrue(v.policy_status(rows[0],{'youtube':{'review_ref':'receipt','review_expires_at':'2000-01-01T00:00:00Z','derived_metrics_allowed':True}}).startswith('blocked'))


if __name__ == '__main__': unittest.main()
