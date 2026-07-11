# Candidate Discovery And Coverage Gate

Use this reference for open-ended news sweeps, radar runs, and delta refreshes.
The goal is high recall before scoring, followed by explicit, source-backed
ranking.

## Signal Separation

Keep two useful but different products separate:

- A feed-outlier scan asks which individual posts traveled unusually far
  relative to their authors' follower bases.
- A news heat check asks which canonical story clusters are commanding the most
  timely market attention and are most useful to the target audience.

Use low-follower/high-view posts as evidence for `audience_breakout` and
independent spread. Do not use them as the candidate universe or the full heat
decision. A major official announcement can be hot through exceptional absolute
velocity, deep discussion, broad independent spread, and acceleration even when
its views/follower ratio is ordinary. Conversely, one extreme account-relative
outlier does not make its underlying story broadly hot without confirmation.

## Candidate Passes

1. Sweep primary surfaces.
   - Check relevant company, founder, product, research, API, release-note, and
     changelog surfaces.
   - Treat a supplied watchlist as a seed, not a closed universe.
2. Sweep independent surfaces.
   - Check time-bounded news/search results, Hacker News top/new/search, relevant
     Reddit communities, social search/outliers, and video/search lift.
   - Check GitHub and Product Hunt only when the story has a developer-product
     or repository surface.
3. Promote secondary references.
   - When a post, article, or discussion mentions a launch, funding event,
     model, or product update, create a candidate cluster and resolve its
     canonical primary announcement.
4. Normalize candidates.
   - Merge aliases and duplicate submissions.
   - Preserve distinct events from the same company as separate clusters.

## Candidate Record

Preserve at least:

| Field | Meaning |
| --- | --- |
| Cluster | Normalized story name |
| First seen | Earliest observed timestamp |
| Primary URL | Canonical announcement or best available primary source |
| Discovery paths | Official, feed, search, HN, Reddit, video, GitHub, or news |
| Secondary URLs | Independent posts and discussions used to discover/confirm it |
| Status | Score, omit, or unresolved |
| Reason | Evidence-based inclusion, omission, or unresolved-source reason |

## Coverage Gate

Do not finalize the heat table until all checks pass:

- Resolve every secondary launch reaction to a primary announcement or label it
  `primary unresolved`.
- Score every canonical announcement showing exceptional early velocity,
  follower-adjusted reach, or independent discussion.
- Resolve every breakout Hacker News, Reddit, news, or video cluster to its
  underlying event.
- Compare the strongest `3-8` clusters side by side before compressing them into
  themes or writing a public derivative.
- List plausible high-signal candidates that were omitted and state why.

An unavailable source is a gap. A story is not absent merely because it did not
appear in a personalized feed.

## Delta Refresh

For a later same-day refresh:

1. Read the earlier snapshot and its candidate audit.
2. Find events first published after that snapshot.
3. Recheck prior `watch`, `rising`, and `hot` clusters for acceleration,
   cross-platform spread, and action-threshold changes.
4. Report only new clusters, material metric changes, stage changes, and action
   changes; link to the earlier table for unchanged context.
5. Mark `single segment` and `drop-everything` clusters as promotion candidates.

Do not infer historical velocity from a later cumulative counter. Preserve both
snapshot times and label any missing earlier counter.

## Public-Derivative Gate

Treat the heat check as research input, not automatic publication. A wrapper
may authorize a local public-safe derivative when:

- the action is `single segment` or `drop-everything`;
- the primary source and decisive metrics are verified;
- the audience-fit angle is concrete; and
- private strategy, personal context, and unsupported adoption claims are
  removed.

Never post, push, or publish externally without separate authorization.
