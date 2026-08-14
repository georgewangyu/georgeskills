# YouTube Market Gap Scoring Rubric

Use this rubric after collecting demand outliers and a separate recent-supply
sample. Scores are directional evidence, not statistical market size.

## Required evidence

| Dimension | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Independent demand | No credible breakout | One credible outlier | Two independent outlier channels | Three or more independent channels across dates |
| Repeatability | Viral accident | Same creator cannot repeat | Same creator or close format repeats | Multiple creators repeat the audience promise |
| Scarcity | Crowded or unmeasured | Some supply pressure | Few strong recent uploads | Demand repeats materially faster than quality supply |
| Defensibility | Easily copied commodity | Minor execution barrier | Skill, access, or production barrier | Compounding access, expertise, data, or community advantage |
| Idea headroom | Fewer than 10 credible ideas | 10-20 | 20-40 | More than 40 without premise dilution |
| Creator fit | Misaligned | Possible but costly | Strong existing capability | Existing proof, assets, access, and audience bridge |

## Default evidence thresholds

- Strong video: `>=10x` recent-channel median.
- Secondary video: `>=5x` recent-channel median.
- Subscriber asymmetry: `>=5` views per current subscriber.
- High asymmetry: `>=20` views per current subscriber.
- Demand confirmation: two independent strong channels or one channel with
  two strong videos.
- Supply density: relevant original uploads per week across `5-10` query
  variants. Preserve the raw count and irrelevant-result rate.

These defaults should move with the category. A costly documentary may need a
longer time window and lower upload-density expectation than a screen-recorded
tutorial.

## Decision labels

- `enter`: demand confirmed, scarcity measured, integrity acceptable,
  defensibility at least `2`, and creator fit at least `2`.
- `pilot`: promising evidence, but one important dimension still needs a
  bounded real-world test.
- `watch`: discovery signal exists, but confirmation or timing is incomplete.
- `reject`: crowded, non-portable, unsafe, rights-compromised, synthetic, or
  structurally misaligned.

## False-positive audit

Check:

- current subscribers inflated after the breakout;
- Shorts or loops leaking into long-form;
- celebrity, press, or existing off-platform distribution;
- copied, licensed, or reused footage;
- synthetic or mass-produced channels;
- staged or exploitative rescue/medical content;
- misleading query matches;
- one channel represented multiple times but mistaken for independent demand;
- baseline distortion from a channel mixing Shorts and long-form;
- high raw views with weak current velocity;
- apparent scarcity caused by narrow vocabulary or collector failure.
