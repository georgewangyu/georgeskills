---
name: news-heat-check-ops
description: Measure the current virality, velocity, and editorial usefulness of a news story, product launch, model release, funding event, or trend. Use when the user asks for a heat score, asks how hot/viral/trending something is, wants to compare competing news waves, decide whether a topic is worth covering now, distinguish mass attention from niche audience fit, or audit why a radar missed a high-signal canonical announcement.
memory_tags:
  - domain:research
  - workflow:news-heat-check
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:current-sources
  - outputs:heat-score
  - risk:medium
---

# News Heat Check Ops

Produce a source-backed, point-in-time heat comparison without confusing a
large account's owned distribution with genuine breakout.

## Inputs

- One or more topics, announcements, URLs, or candidate stories.
- Optional: geography, audience, editorial lane, comparison topic, and time
  window. Default to the last 24 hours and the user's apparent audience.
- Optional: a historical breakout to use as a calibration reference.

## Workflow

1. Define the snapshot.
   - Record the timezone, snapshot time, and comparison window.
   - Treat counters as point-in-time observations that will continue moving.
2. Build the candidate universe.
   - For a multi-story radar or open-ended sweep, read
     [candidate-discovery.md](references/candidate-discovery.md) and complete
     its coverage gate before ranking.
   - Search primary announcement surfaces and independent discovery surfaces;
     do not begin from the personalized feed alone.
   - For a single user-supplied topic, skip the broad universe sweep but still
     resolve the primary announcement.
3. Resolve story clusters.
   - Group aliases, product names, company names, and duplicate submissions
     into one story cluster.
   - Keep similarly named but distinct stories separate.
   - Treat a secondary post that references a launch as a candidate-discovery
     event. Resolve it back to the canonical announcement even when the
     official account or post did not appear in the user's feed.
   - Treat personalized feeds as one discovery surface, not the candidate
     universe.
4. Find the primary evidence.
   - Start with official announcement posts/pages and direct discussion links.
   - Before ranking, audit every launch cluster for the company, founder, or
     official product announcement that best represents the primary event.
   - Browse current sources; do not answer a live heat question from memory.
5. Measure the available surfaces.
   - Social: views, engagement, publication time, author followers, secondary
     posts, and post-count velocity.
   - Discussion: Hacker News points/comments, Reddit conversations, replies,
     quotes, and substantive follow-on analysis.
   - Video/search: YouTube views per hour, short-form crossover, Google search
     lift, and news coverage when available.
   - Developer signals: GitHub star/event velocity only when the story has a
     relevant repository.
6. Calculate comparable signals.
   - Views/hour = observed views / hours since publication.
   - Views/follower = observed views / current author followers. Label current
     followers as a conservative proxy when historical followers are missing.
   - Separate one large owned post from distributed cross-account saturation.
7. Score two different questions.
   - `attention_heat`: velocity, follower-adjusted breakout, cross-platform
     spread, discussion depth, and acceleration.
   - `audience_fit`: usefulness, demoability, novelty, relevance, and the
     availability of a distinctive angle for the stated audience.
   - Read [scoring.md](references/scoring.md) for the rubric and evidence rules.
   - Optionally run `scripts/score_heat.py` after assigning component scores.
8. Make the editorial call.
   - Label each cluster `watch`, `rising`, `hot`, `peaking`, or `cooling`.
   - Recommend `ignore`, `mention`, `single segment`, or `drop-everything`.
   - Explain the strongest evidence, the most important caveat, and what would
     change the decision.

## Priority Order

When time is constrained:

1. Candidate coverage gate and canonical primary resolution.
2. Primary announcement metrics and timestamp.
3. Views/hour and follower-adjusted breakout.
4. Hacker News/Reddit discussion depth.
5. Cross-account and cross-platform spread.
6. Search, video, GitHub, and paid-tool confirmation.

Do not spend the entire budget filling every source. Missing data is a labeled
gap, not a zero.

## Output Contract

Return:

1. Snapshot time and scope.
2. A side-by-side table with raw metrics, `attention_heat`, `audience_fit`,
   stage, action, and confidence.
3. A short explanation of owned reach versus breakout reach.
4. A verdict for each story and the best timely angle, if one exists.
5. Direct links beside the claims they support.
6. Source gaps and historical-counter caveats.
7. For multi-story sweeps, a compact coverage audit listing high-signal
   candidates considered but omitted and the reason for each omission.

When writing to a radar or research artifact, put this comparison before long
source inventories.

## Guardrails

- For routine or automated X reads, use the Bird-style browser-session path
  (`AUTH_TOKEN` + `CT0`) through XBot or IgnitionBot. Do not use an X developer
  bearer token or the official recent-search endpoint, and never fall back to
  a billable official read when session search fails. Record stale session or
  GraphQL query IDs as a source gap.
- Do not call a story viral from raw views alone.
- Do not treat a personalized feed or saved seed list as the market universe.
- Do not substitute a low-follower/high-view outlier scan for event-level news
  detection. Account-relative breakout is one scoring component, not the
  candidate generator or the complete heat score.
- Do not leave a secondary launch reaction unclustered when the canonical
  announcement can be resolved.
- Do not compare lifetime counters as if they were equal-age observations.
- Do not infer historical velocity from a current cumulative counter.
- Do not treat press volume, followers, downloads, or GitHub stars as proof of
  adoption, revenue, or retention.
- Keep evidence and interpretation visibly separate.
- Treat scores as editorial heuristics until calibrated against actual content
  performance.
