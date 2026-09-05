# Trend Lifecycle Case Schema

## Folder Contract

```text
<trend_root>/
  INDEX.md
  YYYY-MM-DD_<trend-slug>/
    case.md
    evidence.jsonl
```

`trend-slug` must be a stable, subject-free kebab-case description of the
format grammar. Keep evidence append-only. Create a `snapshots/` directory only
when real assets exist.

## Required Case Frontmatter

```yaml
trend_case_schema: "shortform-trend-lifecycle-v1"
trend_id: "YYYY-MM-DD_<trend-slug>"
title: "Human-readable title"
discovered_on: "YYYY-MM-DD"
snapshot_at: "YYYY-MM-DDTHH:MM:SSZ"
platforms: "unknown"
earliest_source_backed_at: null
first_breakout_at: null
copy_wave_onset_at: null
peak_at: null
decay_onset_at: null
current_stage: "unknown"
usable_window: "unknown"
confidence: "low"
```

Dates may remain `null` while research is incomplete. `current_stage` must be
one of:

```text
seed | emerging | accelerating | peaking | saturating | decaying | dormant |
reviving | platform-split | unknown
```

`usable_window` must begin with one of:

```text
act-now | adapt-with-mutation | watch | direct-copy-exhausted | unknown
```

## Executable Field Contract

- The case directory basename must equal `trend_id`.
- `trend_id` must be `YYYY-MM-DD_<kebab-case-slug>` and its date prefix must
  equal `discovered_on`.
- `title` and `platforms` must be non-empty strings.
- `snapshot_at` must be an ISO 8601 timestamp with an explicit timezone.
- Every lifecycle milestone field ending in `_at` must be either an ISO 8601
  calendar date/timestamp or YAML `null`. Do not store prose, approximate
  months, ranges, or evidence explanations in these fields.
- When an exact milestone date is unknown, use `null` and put the bounded
  interval plus evidence in `Lifecycle Card`, `Observed Evidence`, or
  `Confidence and Gaps`.
- Known milestones must respect lifecycle order: onset cannot follow any later
  milestone; breakout and copy-wave onset cannot follow peak; peak cannot
  follow decay onset.
- `confidence` is exactly `low`, `medium`, or `high`.
- `published_at` in `evidence.jsonl` may be `null` when the exact post date is
  unavailable; explain the bounded date evidence in `notes`. `observed_at`
  must always be a valid ISO date/timestamp.

## Required Sections

- `## Decision`
- `## Format Grammar`
- `## Lifecycle Card`
- `## Observed Evidence`
- `## Source and Credit Lineage`
- `## Replication and Velocity`
- `## Remaining Usable Window`
- `## Adaptation Boundary`
- `## Inference`
- `## Confidence and Gaps`
- `## Collection Receipt`

## Evidence JSONL

Each non-empty line is one JSON object:

```json
{
  "evidence_id": "instagram-Dabc123-2026-09-01T18:00:00Z",
  "platform": "instagram",
  "url": "https://www.instagram.com/reel/Dabc123/",
  "creator": "public-handle",
  "published_at": "2026-08-31T17:00:00Z",
  "observed_at": "2026-09-01T18:00:00Z",
  "views": null,
  "likes": 12000,
  "comments": 94,
  "shares": null,
  "followers": null,
  "role": "breakout_mutation",
  "credit_targets": [],
  "format_match": "confirmed",
  "source_class": "platform_public",
  "notes": "Public counter snapshot; views unavailable."
}
```

Required keys are `evidence_id`, `platform`, `url`, `creator`, `published_at`,
`observed_at`, `role`, `format_match`, and `source_class`. Metric values must be
non-negative integers or `null`.

Allowed roles:

```text
source_candidate | breakout_mutation | independent_copy | parent_ancestor |
negative_control | metric_snapshot
```

Allowed format matches: `confirmed`, `probable`, `rejected`.

## Confidence Rule

Confidence describes evidence coverage, not rhetorical certainty:

- `high`: direct dates/links plus broad enough replication and time evidence;
- `medium`: strong bounded case with a material platform or history gap;
- `low`: sparse examples, unverifiable counters, or inference-dominant timing.
