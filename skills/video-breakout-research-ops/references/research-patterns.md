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

## Minimal Artifact Shape

A good final artifact usually has:
- ranked creators/posts
- concept clusters
- a short note on why each cluster works
- 1 to 3 adaptation ideas per cluster
- explicit caveats on data quality
