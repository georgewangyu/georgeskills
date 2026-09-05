# Candidate Discovery Sources

Discovery sources nominate cases. They do not determine the lifecycle.

## Public Trend-Guide Sites

### Real Time Trend Alerts

URL: <https://www.realtimetrendalert.com/>

Useful fields:

- regularly updated cross-platform trend-guide index;
- platform and category labels;
- concise format/vibe description;
- practical recreation steps;
- multiple canonical example links on many guide pages;
- page publication/update date.

Missing proof:

- no visible historical metric snapshots;
- no creator-relative baselines;
- no explicit independent-creator count or replication velocity;
- no documented onset, peak, decay, or confidence calculation;
- guide publication date is not trend-onset date.

Use it as a daily nomination feed and example-link bridge. Never equate its
ordering or `rising` language with a verified lifecycle state.

## Open-Source Components Worth Inspecting

### mvanhorn/last30days-skill

URL: <https://github.com/mvanhorn/last30days-skill>

MIT-licensed multi-source research orchestration with source adapters,
diagnostics, normalized scoring, historical `as-of` support, and watchlist
deltas. Strong reference for adapter contracts, provenance, source health, and
cross-source normalization. It is topic/community research, not an exact video-
grammar lifecycle detector.

### openclaw-easy/ViralMint

URL: <https://github.com/openclaw-easy/ViralMint>

AGPL-3.0 local-first video pipeline with Scout services for channel-relative
outliers, view velocity, Google Trends, and TikTok/YouTube/Douyin collection.
Useful architectural reference for candidate scoring and service boundaries.
Do not copy code into a differently licensed project without an explicit AGPL
decision. Its publishing and generation surfaces are outside this skill.

### princepal9120/tkt-cli

URL: <https://github.com/princepal9120/tkt-cli>

Early-stage TikTok CLI exposing JSON for trending, hashtag, search, profile,
video, competitor, and growth queries. Potential TikTok collector adapter, but
the repository is young and its API stability, access method, terms boundary,
and effective license must be verified before adoption.

### AdrienGuille/SONDY and cbuntain/BurstyTwitterStreams

URLs:

- <https://github.com/AdrienGuille/SONDY>
- <https://github.com/cbuntain/BurstyTwitterStreams>

Older open-source references for event detection, influence analysis, and burst
detection over social time series. Useful for algorithm ideas and known-trend
replay, not as modern Instagram/TikTok collectors.

## Platform and Provider Surfaces

- Official or approved platform APIs: preferred when they expose the required
  fields and research access is available.
- TikTok Creative Center: useful for regional hashtag/ad nomination, but its
  currently exposed public surfaces and historical depth change over time.
- Approved commercial collectors: acceptable as bounded source adapters when
  canonical URLs, published timestamps, observed timestamps, and raw counters
  are preserved.
- Manual browser inspection: useful for source credit, visual grammar, and
  counter verification; record the method and observation time.

## Adapter Contract

Every adapter should return, when available:

```text
platform
canonical_url
post_id
creator_id_or_handle
published_at
observed_at
views likes comments shares
followers
caption_or_title
transcript
ocr_text
audio_id
credit_targets
collector_name
collector_version
raw_evidence_ref
```

The join layer—not the provider—owns deduplication, format matching, creator
independence, lifecycle state, and usable-window decisions.
