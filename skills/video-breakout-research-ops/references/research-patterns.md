# Video Breakout Research Patterns

## Goal

Find concept-level asymmetry, not just big numbers.

The ideal target looks like:
- low or moderate follower base
- at least one short-form post with disproportionately high reach
- evidence the performance came from a portable format, hook, or promise
- signals that the result is fresh enough to matter now

## Practical Search Surfaces

Treat these as starting points, not guarantees:
- first-party platform search around niche keywords and adjacent terms
- profile pages of low-to-mid follower creators already known in the niche
- public web results that expose post URLs, profile titles, or snippets
- manually reviewed shortlists from trend newsletters, community threads, or creator roundups

For YouTube Shorts, public search and metadata are usually easier to probe.
For TikTok and Instagram, expect more volatility and use browser fallback only when needed.

## Suggested Research Passes

### Pass 1: Seed Sweep

Start with:
- 5 to 15 niche keywords
- 10 to 30 candidate creators
- 2 to 5 posts per creator

Goal:
- build the first worksheet, not the final answer

### Pass 2: Asymmetry Sort

Sort by:
- highest view-to-follower mismatch
- multiple strong posts from the same creator
- concepts repeated by more than one creator

Goal:
- separate real patterns from noise

### Pass 3: Portability Filter

Reject or penalize concepts that depend on:
- celebrity or pre-existing fame
- unusual access or expensive props
- a body, face, voice, or life context the user cannot plausibly reproduce
- platform-native luck without a clear content mechanic

Keep concepts that can be rewritten into:
- a new hook
- a new niche promise
- the same visual grammar with different substance

### Pass 4: Follower-Conversion Review

Only run this pass when post-attributed follow data or a clearly labeled
creator-provided insight is available. Record:

- follows/views and follows/reach
- average watch percentage within a comparable duration band
- saves/views and shares/views
- continuity between the post promise and profile promise
- series or open-loop design
- topic-to-profile fit
- CTA type and whether a follow gate influenced the result
- attribution source and confidence

Keep this lane separate from the view-breakout rank. A post can be a strong
attention breakout and a weak follower converter, or vice versa.

## Scoring Notes

### Base Asymmetry

Use:
- `log10(views + 1) - log10(followers + 1)`

Interpretation:
- near `0`: roughly proportionate reach
- `> 1`: meaningfully outsized reach relative to base
- `> 2`: very strong asymmetry, worth manual review

### Helpful Bonuses

- repeatability: creator has multiple breakout posts
- recency: recent performance carries more weight
- engagement quality: comments and shares improve confidence when available
- portability: concept seems transferable to another creator or niche

### Helpful Penalties

- saturation: same format is clearly exhausted
- identity lock-in: results depend on persona rather than concept
- credibility issue: follower count or audience size looks understated relative to obvious fame
- incomplete data: uncertain views, missing follower counts, or stale probes

## Follower-Conversion Calibration

Use ratios as comparative research signals, not universal platform
benchmarks. Compare similar formats and duration bands whenever possible.

Suggested starting bands for manual triage:

| Signal | Low | Notable | Strong | Exceptional |
| --- | ---: | ---: | ---: | ---: |
| Follows / views | `<0.10%` | `0.10-0.30%` | `0.30-1.00%` | `>=1.00%` |
| Follows / reach | `<0.15%` | `0.15-0.50%` | `0.50-1.50%` | `>=1.50%` |
| Saves / views | `<0.10%` | `0.10-0.30%` | `0.30-0.75%` | `>=0.75%` |
| Shares / views | `<0.05%` | `0.05-0.15%` | `0.15-0.40%` | `>=0.40%` |

Average watch percentage is strongly duration-dependent. Use it to compare
like-for-like posts, not a 20-second clip against a 20-minute video.

### CTA Classification

- `none`: no explicit conversion request observed
- `implicit_series`: continuity comes from a series or open loop
- `direct_follow`: a transparent request to follow for the stated promise
- `keyword_dm`: a comment keyword triggers a resource or message
- `follow_gated_asset`: the promised resource requires or encourages a follow

Keyword-DM and follow-gated results are hybrid funnel outcomes. Report the
observed conversion, but do not label it content-only conversion.

### Evidence Classes

- `platform_first_party`: exported or directly observed platform insight
- `creator_first_party`: insight shown or stated by the creator; not audited
- `public_metadata`: visible counters and metadata without follow attribution
- `inferred`: derived from indirect evidence
- `unknown`: source cannot be established

Evidence confidence and conversion strength are separate dimensions. Never
raise the confidence label merely because the result is large.

## Minimal Artifact Shape

A good final artifact usually has:
- ranked creators/posts
- concept clusters
- a short note on why each cluster works
- 1 to 3 adaptation ideas per cluster
- explicit caveats on data quality
