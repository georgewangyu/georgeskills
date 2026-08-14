---
name: youtube-market-gap-radar-ops
description: Find and validate low-supply, high-demand YouTube niches using low-subscriber breakout videos, channel-baseline outliers, repeated demand, and query-family supply audits. Use when someone asks for YouTube market gaps, underserved video genres, small channels with unusually large videos, categories worth entering, or a repeatable supply-versus-demand scan. Do not use for one-channel checks, cross-platform Shorts research, or recurring creator watchlists.
---

# YouTube Market Gap Radar

Find category opportunities rather than isolated viral videos. Treat one
outlier as discovery, repeated outliers as demand confirmation, and a separate
upload-density audit as the evidence required to claim scarce supply.

## Inputs

- Seed category or audience.
- Content format: long-form, Shorts, or separate scans of both.
- Subscriber cap, minimum views, recency window, language, and region.
- Optional production, rights, safety, or creator-fit constraints.
- Local `youtubebot` directory through `--youtube-bot-dir` or
  `YOUTUBEBOT_DIR`.

## Workflow

1. **Expand the category into search lanes.**
   - Create `8-20` lanes across subject, audience promise, mechanism, format,
     transformation, question, and adjacent vocabulary.
   - Keep long-form and Shorts in separate result sets.
   - Include exact solution language and plain audience language.

2. **Run the demand sweep.**
   - Prefer the official-API `youtubebot` collector because it returns current
     subscriber counts and recent-channel baselines.
   - Run `scripts/run_youtube_market_gap.py` so every completed lane is
     checkpointed before the next query.
   - Start with channels below `100K` subscribers, videos above `50K-100K`
     views, the last `365` days, and videos longer than four minutes.
   - Rank true channel-baseline multiplier before views/current subscribers.

3. **Separate discovery from confirmation.**
   - `discovery`: one credible outlier.
   - `confirmed demand`: at least two independent small channels, or one small
     channel with two credible outliers, carrying the same audience promise.
   - `durable demand`: the pattern repeats across dates, creators, and close
     query variants.
   - Do not count duplicate uploads, compilations of the same footage, or
     channels with hidden off-platform fame as independent evidence.

4. **Audit supply separately.**
   - Expand each confirmed cluster into `5-10` synonym queries.
   - Search recent uploads ordered by date, not only by views.
   - Count relevant, original, sufficiently good uploads per week.
   - Record irrelevant-query rate, independent creators, production quality,
     and how often new supply reaches the audience threshold.
   - Do not infer scarcity from zero results until query wording and collector
     coverage have been checked.

5. **Review quality and defensibility.**
   - Reject synthetic spam, fake or staged rescue, graphic exploitation,
     copied footage, rights ambiguity, misleading titles, mislabeled Shorts,
     and concepts dependent on celebrities or institutional distribution.
   - Preserve production barrier, access to subject matter, repeatable idea
     headroom, monetization fit, and creator advantage as separate judgments.

6. **Score and decide.**
   - Read `references/scoring-rubric.md`.
   - Label each cluster `enter`, `pilot`, `watch`, or `reject`.
   - A cluster cannot receive `enter` while supply remains unmeasured.

## Collector Command

```bash
python3 skills/youtube-market-gap-radar-ops/scripts/run_youtube_market_gap.py \
  --youtube-bot-dir <path-to-youtubebot> \
  --lane "dog grooming transformation" \
  --lane "matted rescue dog grooming" \
  --lane "dog grooming emergency" \
  --max-subs 100000 \
  --min-views 50000 \
  --days 365 \
  --content-type long \
  --video-duration medium \
  --out /tmp/youtube-market-gap.json
```

If the API quota is exhausted, retain the checkpointed output, report the
unfinished lanes, and resume after reset. Public YouTube search or connected
third-party tools may provide discovery-only fallback evidence, but label it
lower confidence when channel baselines are unavailable.

## Output Contract

Return:

- Search frame and thresholds.
- Completed, empty, and failed lanes.
- Ranked video evidence with URL, publication date and age, current
  subscribers, views, views/subscribers, channel baseline, outlier multiplier,
  and velocity.
- Cluster scorecards with independent-channel count and repeat evidence.
- Separate demand and supply conclusions.
- Quality, rights, safety, and denominator caveats.
- `enter`, `pilot`, `watch`, or `reject` decision with the next smallest test.

## Boundaries

- Use `video-breakout-research-ops` for cross-platform short-form breakout
  concepts.
- Use `niche-video-watchlist-ops` for a known niche or recurring creator list.
- Use `youtube-check-ops` for one channel or video.
- Never call a category low-supply based only on views/subscribers or one
  viral upload.
