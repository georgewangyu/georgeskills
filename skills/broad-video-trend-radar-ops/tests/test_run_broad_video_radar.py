import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
import pytest
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run_broad_video_radar.py'
spec = importlib.util.spec_from_file_location('broad_radar_test', SCRIPT)
broad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(broad)

def args(output):
    with patch.object(sys, 'argv', [str(SCRIPT), '--platform','youtube','--youtube-bot-dir','synthetic','--lane','topic','--out',str(output)]):
        return broad.parse_args()
def review():
    return {'sources': {'youtube_data_api': {'platform':'youtube',
        'data_class':'non_authorized_public_metadata','basis_ref':'synthetic-only',
        'review_expires_at':'2099-01-01T00:00:00Z','metadata_collection_allowed':True,
        'metadata_storage_allowed':True,'max_storage_days':30,'max_freshness_days':7}}}

def test_missing_or_expired_review_never_invokes_collector(tmp_path):
    for basis in ({}, review()):
        if basis: basis['sources']['youtube_data_api']['review_expires_at']='2000-01-01T00:00:00Z'
        settings=args(tmp_path/'out'); settings._retention_review=basis
        with patch.object(broad, 'run_json') as run:
            assert broad.collect(settings) == []
            run.assert_not_called()

def test_missing_timestamp_and_cached_scores_are_not_persisted(tmp_path):
    settings=args(tmp_path/'out');settings._retention_review=review()
    raw={'platform':'youtube','source':'youtube_data_api','data_class':'non_authorized_public_metadata','id':'v','views':100,'baselineViews':999,'outlierScore':99}
    with patch.object(broad,'run_json',return_value=[raw]):
        assert broad.collect(settings)==[]
    raw['observed_at']=datetime.now(timezone.utc).isoformat()
    with patch.object(broad,'run_json',return_value=[raw]):
        rows=broad.collect(settings)
    assert rows[0]['observed_at']==raw['observed_at']
    assert rows[0]['baseline_views'] is None
    assert 'outlierScore' not in rows[0]['source_fields']

def test_existing_output_preserved_before_collection(tmp_path):
    output=tmp_path/'out';output.write_text('known good')
    with patch.object(broad,'parse_args',return_value=args(output)), patch.object(broad,'collect') as run:
        with pytest.raises(FileExistsError): broad.main()
        run.assert_not_called()
    assert output.read_text()=='known good'
