# Scoring Reference

## Attention Heat

Assign each component a score from `0-100`, preserve the raw evidence used,
then calculate:

| Component | Weight | What it measures |
| --- | ---: | --- |
| Social velocity | 30% | Views/hour, post volume/hour, and early reach |
| Audience breakout | 20% | Views/follower and reach beyond owned audiences |
| Cross-platform spread | 20% | Independent spread across social, discussion, video, search, news, and developer surfaces |
| Discussion depth | 15% | Comments, replies, quotes, bookmarks, and substantive follow-on analysis |
| Acceleration | 15% | Whether recent velocity is increasing relative to earlier windows or the topic's baseline |

`attention_heat = velocity*.30 + breakout*.20 + spread*.20 + depth*.15 + acceleration*.15`

## Audience Fit

The second score answers whether the story is useful for the stated audience,
not whether the whole internet cares.

| Component | Weight |
| --- | ---: |
| Audience relevance | 25% |
| Demoability / proof potential | 20% |
| Novelty | 20% |
| Distinctive angle | 20% |
| Actionability | 15% |

## Editorial Actions

Use these as starting thresholds, then calibrate against actual performance:

| Condition | Default action |
| --- | --- |
| Heat `>=90` and fit `>=75` | `drop-everything` |
| Heat `>=70` and fit `>=65` | `single segment` |
| Heat `>=45` and fit `>=60` | `mention` |
| Otherwise | `ignore` (`watch` remains the stage label) |

Override a threshold when the raw evidence clearly supports a different call,
but state why.

## Stage Labels

- `watch`: weak or incomplete signal; monitor for another confirming surface.
- `rising`: recent velocity is increasing and new accounts/surfaces are joining.
- `hot`: strong current velocity with independent confirmation.
- `peaking`: very high attention, but acceleration is flattening.
- `cooling`: attention remains visible while recent velocity declines.

## Confidence

- `high`: primary links plus multiple independent surfaces and comparable-age
  metrics.
- `medium`: strong primary evidence with one or two meaningful gaps.
- `low`: retrospective counters, search snippets, missing timestamps, or weak
  cross-platform confirmation.

## Evidence Notes

- Record the exact snapshot time.
- Prefer metrics from primary posts and platform APIs/visible counters.
- For historical comparisons, distinguish contemporaneous captures from
  current cumulative counts.
- If historical follower counts are unavailable, label current followers as a
  conservative denominator rather than implying they were the launch-time base.
- One celebrity or company account can create huge owned reach. Distributed
  saturation requires independent accounts, communities, and platforms.

## Scoring Helper Input

Pass one object or an array of objects to `scripts/score_heat.py`:

```json
{
  "topic": "Example model launch",
  "attention": {
    "social_velocity": 90,
    "audience_breakout": 75,
    "cross_platform_spread": 80,
    "discussion_depth": 70,
    "acceleration": 85
  },
  "audience_fit": {
    "audience_relevance": 95,
    "demoability": 90,
    "novelty": 80,
    "distinctive_angle": 85,
    "actionability": 90
  }
}
```
