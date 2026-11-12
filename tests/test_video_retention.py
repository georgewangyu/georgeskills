import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from video_retention import collection_permission, eligible_observations

NOW = datetime(2026, 11, 12, tzinfo=timezone.utc)
def review(derived=False):
    return {'sources': {'youtube_data_api': {'platform':'youtube',
        'data_class':'non_authorized_public_metadata', 'basis_ref':'synthetic-only',
        'review_expires_at':'2026-12-01T00:00:00Z', 'metadata_storage_allowed':True,
        'metadata_collection_allowed':True, 'derived_metrics_allowed':derived,
        'max_storage_days':30, 'max_freshness_days':7}}}
def row(ident):
    return {'platform':'youtube', 'source':'youtube_data_api',
        'data_class':'non_authorized_public_metadata', 'observed_at':NOW.isoformat(),
        'id':ident, 'channelId':'creator', 'durationSeconds':30,
        'publishedAt':'2026-11-10T00:00:00Z', 'views':100}

def test_baseline_requires_explicit_derived_permission():
    raw = {**row('main'), 'baselineVideos':[row(str(i)) for i in range(3)], 'baselineViews':999}
    for allowed in (False, True):
        rows, excluded = eligible_observations([raw], review(allowed), NOW)
        assert not excluded
        assert rows[0]['baseline_status'] == ('comparable' if allowed else 'unavailable')
        assert rows[0]['baseline_views'] == (100 if allowed else None)

def test_exact_collection_permission():
    assert collection_permission(review(), 'youtube_data_api', 'youtube', now=NOW)['allowed']
    for case in ('missing', 'expired', 'class', 'platform', 'unrelated'):
        basis = review()
        policy = basis['sources']['youtube_data_api']
        if case == 'missing': policy.pop('metadata_collection_allowed')
        if case == 'expired': policy['review_expires_at'] = '2000-01-01T00:00:00Z'
        if case == 'class': policy['data_class'] = 'other'
        if case == 'platform': policy['platform'] = 'other'
        if case == 'unrelated': basis['sources'] = {}
        assert not collection_permission(basis, 'youtube_data_api', 'youtube', now=NOW)['allowed'], case
