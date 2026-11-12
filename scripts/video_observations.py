"""Portable, offline video evidence adapters. No collection or account actions."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def number(value):
    if value is None or value == '' or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError):
        return None


def first(row, *keys):
    return next((row[k] for k in keys if row.get(k) is not None), None)


def public_payload(value):
    """Refuse secret-bearing payloads rather than silently making them durable."""
    if isinstance(value, dict):
        for key, item in value.items():
            if re.search(r'token|password|cookie|authorization|secret|session', str(key), re.I):
                raise ValueError('Secret/session-bearing source fields are not observation metadata')
            public_payload(item)
    elif isinstance(value, list):
        for item in value:
            public_payload(item)
    elif isinstance(value, str) and value.startswith(('https://', 'http://')):
        url = urlsplit(value)
        if url.username or url.password or any(re.search(r'token|secret|password|authorization', k, re.I) for k, _ in parse_qsl(url.query)):
            raise ValueError('Credential-bearing URLs are not observation metadata')
    return value


def canonical_url(value):
    if not value:
        return None
    url = urlsplit(str(value))
    if url.scheme != 'https' or not url.hostname:
        return None
    # YouTube's video identity is in v; stripping every query loses identity.
    if url.hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com'} and url.path == '/watch':
        video = dict(parse_qsl(url.query)).get('v')
        return f'https://www.youtube.com/watch?v={video}' if video else None
    return urlunsplit((url.scheme, url.netloc, url.path.rstrip('/'), '', ''))


def observation(row, platform=None, observed_at=None):
    public_payload(row)
    result = dict(row)  # Preserve the public source fields and legacy consumer keys.
    platform = platform or row.get('platform')
    url = canonical_url(first(row, 'canonical_url', 'post_url', 'url'))
    ident = first(row, 'video_id', 'id')
    if not ident and url:
        ident = dict(parse_qsl(urlsplit(url).query)).get('v') or urlsplit(url).path.split('/')[-1]
    published = first(row, 'published_at', 'publishedAt', 'postedAt')
    captured = first(row, 'observed_at', 'collected_at') or observed_at
    creator = first(row, 'creator_handle', 'creator', 'channel', 'channelTitle')
    fields = {
        'views': ('views',), 'likes': ('likes',), 'comments': ('comments',),
        'shares': ('shares',), 'saves': ('saves', 'saved'), 'follows': ('follows',),
        'reach': ('reach', 'accounts_reached'),
    }
    metrics = {key: number(first(row, *aliases) if first(row, *aliases) is not None else row.get('metrics', {}).get(key)) for key, aliases in fields.items()}
    now, then = timestamp(captured), timestamp(published)
    age = (now - then).total_seconds() / 86400 if now and then and now >= then else None
    result.update({
        'schema': 'video-observation-v1', 'platform': platform,
        '_series_annotation_confirmed': False,
        'video_id': str(ident) if ident else None, 'canonical_url': url,
        'creator_id': first(row, 'creator_id', 'channelId'),
        'creator_handle': creator, 'followers': number(first(row, 'followers', 'subscribers', 'base')),
        'published_at': published, 'observed_at': captured,
        'post_age_days': age if age is not None else number(first(row, 'post_age_days', 'age_days')),
        'duration_seconds': number(first(row, 'duration_seconds', 'durationSeconds')),
        'thumbnail': first(row, 'thumbnail', 'thumbnail_url'),
        'baseline_views': number(first(row, 'baseline_views', 'baselineViews')),
        'baseline_members': first(row, 'baseline_members', 'baselineVideos'),
        'metrics': metrics,
        'views': metrics['views'],
        'metric_status': {k: 'observed' if v is not None else 'unavailable' for k, v in metrics.items()},
        'hook_text': first(row, 'hook_text', 'title', 'caption') or '',
        'post_url': url,
        'source_fields': row.get('source_fields', dict(row)),
    })
    return result


def identity(row):
    return row.get('platform'), row.get('video_id') or row.get('canonical_url')


def momentum(current, history):
    """Only actual same-video observations establish interval counter growth."""
    current_time = timestamp(current.get('observed_at'))
    current_views = current.get('metrics', {}).get('views')
    if not current_time or current_views is None:
        return {'status': 'unavailable', 'reason': 'missing timestamp or views'}
    if not identity(current)[1]:
        return {'status': 'unavailable', 'reason': 'missing video identity'}
    samples = {}
    for row in history:
        at = timestamp(row.get('observed_at'))
        views = row.get('metrics', {}).get('views')
        if identity(row) == identity(current) and at and at <= current_time and views is not None:
            if (at == current_time and views != current_views) or (at in samples and samples[at] != views):
                return {'status': 'unavailable', 'reason': 'conflicting observations at one timestamp'}
            if at < current_time:
                samples[at] = views
    pairs = sorted(samples.items())[-2:] + [(current_time, current_views)]
    if len(pairs) < 2:
        return {'status': 'unavailable', 'reason': 'no previous timed observation'}
    intervals = []
    for (start, before), (end, after) in zip(pairs, pairs[1:]):
        if after < before:
            return {'status': 'counter_reset', 'views_per_hour': None}
        hours = (end - start).total_seconds() / 3600
        intervals.append({'from': start.isoformat(), 'to': end.isoformat(),
                          'hours': hours, 'delta_views': after - before,
                          'views_per_hour': (after - before) / hours})
    return {'status': 'observed', **intervals[-1],
            'acceleration_per_hour': ((intervals[-1]['views_per_hour'] - intervals[0]['views_per_hour']) /
                                      ((intervals[-1]['hours'] + intervals[0]['hours']) / 2)) if len(intervals) == 2 else None,
            'intervals': intervals,
            'interpretation': 'counter growth; unequal intervals and platform revisions may affect comparisons'}


def series(row):
    title = row.get('hook_text') or ''
    episode = re.search(r'\b(?:day|episode|ep\.?|part)\s*(\d+)(?:\s*[/]\s*(\d+))?', title, re.I)
    season = re.search(r'\b(?:season|s)\s*(\d+)\b', title, re.I)
    name = row.get('series_name')
    series_id = row.get('series_id')
    creator = row.get('creator_id') or row.get('creator_handle')
    if not creator:
        return {'status': 'unavailable', 'reason': 'missing creator identity'}
    if not (name or series_id or episode):
        return {'status': 'unassigned'}
    # A marker nominates a group; it never confirms shared execution or continuity.
    grammar = name or (re.sub(r'\b(?:day|episode|ep\.?|part)\s*\d+(?:\s*[/]\s*\d+)?', '', title, flags=re.I))
    grammar = re.sub(r'\b(?:season|s)\s*\d+\b', '', grammar, flags=re.I)
    grammar = ' '.join(re.findall(r'\w+', grammar.lower()))
    return {'status': 'explicit' if row.get('_series_annotation_confirmed') and (name or series_id) else 'candidate',
            'series_id': series_id or f'{row.get("platform")}:{creator}:{grammar}',
            'series_name': name or grammar,
            'season': row.get('season') or (int(season[1]) if season else None),
            'episode': row.get('episode') if row.get('episode') is not None else (int(episode[1]) if episode else None),
            'planned_episodes': int(episode[2]) if episode and episode[2] else None,
            'format_id': row.get('format_id'),
            'return_promise': row.get('return_promise'),
            'progress_state': row.get('progress_state')}


def annotate(rows, annotations):
    by_key = {}
    for annotation in annotations:
        key = identity(annotation)
        if key in by_key and by_key[key] != annotation:
            raise ValueError('Conflicting annotations for one video identity')
        by_key[key] = annotation
    result = []
    for row in rows:
        annotation = by_key.get(identity(row), {})
        values = {k: v for k, v in annotation.items()
                  if k in {'series_id', 'series_name', 'season', 'episode', 'format_id',
                           'return_promise', 'progress_state', 'exploration_lane'}}
        confirmed = bool(annotation.get('series_id') or annotation.get('series_name'))
        if confirmed:
            # Do not silently prefer unreviewed source group IDs to reviewed names.
            values['series_id'] = annotation.get('series_id')
            values['series_name'] = annotation.get('series_name')
        result.append({**row, **values, '_series_annotation_confirmed': confirmed})
    return result


def feedback_links(row, feedback):
    if not row.get('video_id'):
        return {'state': 'unreviewed', 'events': [], 'owned_results': []}
    matches = [event for event in feedback if event.get('candidate_id') == row.get('video_id')
               and event.get('platform') == row.get('platform')]
    for event in matches:
        if event.get('state') not in {'selected', 'filmed', 'posted', 'rejected', 'parked'}:
            raise ValueError('Unknown feedback state')
        if not event.get('decision_id') or not timestamp(event.get('decided_at')):
            raise ValueError('Feedback requires decision identity and timestamp')
        if event.get('state') == 'rejected' and not event.get('reason'):
            raise ValueError('Rejection requires a reason; no inferred format blacklist')
        public_payload(event)
        owned = event.get('owned_result')
        if owned and (not owned.get('media_id') or not timestamp(owned.get('observed_at')) or not owned.get('distribution') or not owned.get('source_ref') or owned.get('checkpoint') not in {'24h', '72h'}):
            raise ValueError('Owned results require exact media identity, capture time, distribution and source')
    unique = {}
    for event in matches:
        key = event['decision_id']
        if key in unique and unique[key] != event:
            raise ValueError('Conflicting feedback decision ID')
        unique[key] = event
    events = sorted(unique.values(), key=lambda x: timestamp(x['decided_at']))
    return {'state': events[-1]['state'] if events else 'unreviewed', 'events': events,
            'owned_results': [event['owned_result'] for event in events if event.get('owned_result')],
            'inference': 'links only; no causal performance promotion'}


def diverse_shortlist(rows, limit=10, max_per_creator=2):
    lanes = ('niche', 'adjacent', 'wildcard')
    buckets = {lane: [] for lane in lanes}
    for row in rows:
        if row.get('feedback', {}).get('state') in {'rejected', 'parked', 'filmed', 'posted'}:
            continue
        buckets[row.get('exploration_lane') if row.get('exploration_lane') in lanes else 'niche'].append(row)
    result, seen, creators = [], set(), defaultdict(int)
    while len(result) < limit and any(buckets.values()):
        for lane in lanes:
            if not buckets[lane] or len(result) >= limit:
                continue
            row = buckets[lane].pop(0)
            key = identity(row)
            creator = row.get('platform'), row.get('creator_id') or row.get('creator_handle')
            if key[1] and key not in seen and creators[creator] < max_per_creator:
                result.append(row); seen.add(key); creators[creator] += 1
    return result


def policy_status(row, policies, now=None):
    policy = policies.get(row.get('platform'), {})
    now = now or datetime.now(timezone.utc)
    expires = timestamp(policy.get('review_expires_at'))
    if not policy.get('review_ref') or not expires or expires <= now:
        return 'blocked: missing/current source-rights review'
    collector = row.get('collector') or row.get('source')
    if not collector or collector not in policy.get('collectors', []):
        return 'blocked: collector-specific derived-metric permission not established'
    if policy.get('derived_metrics_allowed') is not True:
        return 'blocked: derived-metric permission not established'
    return 'allowed'
