"""Offline eligibility only. Does not grant rights, refresh, or delete data."""
from datetime import datetime, timedelta, timezone
from statistics import median
from video_observations import timestamp, number, first, observation


def eligibility(row, review, now=None):
    now = now or datetime.now(timezone.utc)
    def blocked(reason):
        return {'eligible': False, 'reason': reason, 'storage_deadline': None, 'freshness_deadline': None}
    if not isinstance(row, dict):
        return blocked('invalid_record')
    source = row.get('collector') or row.get('source')
    sources = review.get('sources', {}) if isinstance(review, dict) else {}
    policy = sources.get(source, {}) if isinstance(sources, dict) and isinstance(source, str) else {}
    if not isinstance(policy, dict):
        return blocked('missing_source_review')
    if not source or not policy:
        return blocked('missing_source_review')
    platform = row.get('platform')
    if platform == 'youtube_long':
        platform = 'youtube'
    if policy.get('platform') != platform or not row.get('data_class') or policy.get('data_class') != row.get('data_class'):
        return blocked('source_class_mismatch')
    expires = timestamp(policy.get('review_expires_at'))
    if not policy.get('basis_ref') or not expires or expires <= now or policy.get('metadata_storage_allowed') is not True:
        return blocked('missing_current_storage_basis')
    storage = number(policy.get('max_storage_days'))
    freshness = number(policy.get('max_freshness_days'))
    if not storage or not freshness or freshness > storage:
        return blocked('missing_safe_deadline')
    # This public Data API class has a documented maximum. No blanket Meta/TikTok TTL.
    if source == 'youtube_data_api':
        if platform != 'youtube' or row.get('data_class') != 'non_authorized_public_metadata' or storage > 30:
            return blocked('unsupported_youtube_storage_basis')
    captured = timestamp(first(row, 'observed_at', 'collected_at'))
    if not captured:
        return blocked('missing_actual_observation_time')
    if captured > now:
        return blocked('future_observation_time')
    try:
        storage_deadline = captured + timedelta(days=storage)
        freshness_deadline = captured + timedelta(days=freshness)
    except OverflowError:
        return blocked('missing_safe_deadline')
    reason = 'expired_storage' if now >= storage_deadline else 'stale_observation' if now >= freshness_deadline else 'eligible'
    return {'eligible': reason == 'eligible', 'reason': reason,
            'storage_deadline': storage_deadline.isoformat(), 'freshness_deadline': freshness_deadline.isoformat()}


DERIVED = {'baseline_views', 'baselineViews', 'baseline_members', 'baselineVideos', 'baselineVideoCount',
           'outlierScore', 'outlier_multiplier', 'score', 'trending', 'momentumScore', 'channel_baseline_views',
           'momentum', 'whyFlagged', 'signalStrength', 'outlier', 'ratio', 'subscriberRatio',
           'viewsPerDay', 'viewsPerFollower', 'baselineMethod', 'velocityMethod'}

def clear_cached_scores(value):
    if isinstance(value, dict):
        return {k: clear_cached_scores(v) for k, v in value.items() if k not in DERIVED and k != 'source_fields'}
    if isinstance(value, list):
        return [clear_cached_scores(v) for v in value]
    return value


def eligible_observations(raw_rows, review, now=None):
    """Filter before dedup/momentum/ranking; reconstruct only proven comparable baselines."""
    now = now or datetime.now(timezone.utc)
    result, excluded = [], []
    for index, raw in enumerate(raw_rows):
        verdict = eligibility(raw, review, now)
        if not verdict['eligible']:
            excluded.append({'row_index': index, **verdict})
            continue
        row = observation(clear_cached_scores(raw))
        peers = []
        # A current outer row does not make nested historic counters current.
        members = first(raw, 'baseline_members', 'baselineVideos') or []
        latest = {}
        for peer in members if isinstance(members, list) else []:
            if not eligibility(peer, review, now)['eligible']:
                continue
            if (peer.get('collector') or peer.get('source')) != (raw.get('collector') or raw.get('source')) or peer.get('data_class') != raw.get('data_class'):
                continue
            item = observation(clear_cached_scores(peer))
            if item['platform'] != row['platform'] or not item['video_id'] or item['video_id'] == row['video_id']:
                continue
            if not row['creator_id'] or item['creator_id'] != row['creator_id']:
                continue
            duration, age = item['duration_seconds'], item['post_age_days']
            if (duration is None or row['duration_seconds'] is None or age is None or
                    not row['post_age_days'] or not row['post_age_days']/2 <= age <= row['post_age_days']*2 or
                    (duration <= 90) != (row['duration_seconds'] <= 90) or item['views'] is None):
                continue
            key = item['video_id']
            if key not in latest or timestamp(item['observed_at']) > timestamp(latest[key]['observed_at']):
                latest[key] = item
        peers = list(latest.values())
        row['baseline_members'] = peers
        row['baseline_views'] = median(item['views'] for item in peers) if len(peers) >= 3 else None
        row['baseline_status'] = 'comparable' if len(peers) >= 3 else 'unavailable'
        row['eligibility'] = verdict
        result.append(row)
    return result, excluded
