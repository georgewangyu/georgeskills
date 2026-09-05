---
name: shortform-trend-lifecycle-ops
description: Trace a short-form video format from its earliest source-backed onset through breakout, replication, peak, decay, and remaining usable window. Use for TikTok, Instagram Reels, or YouTube Shorts trends when one-post outlier research is not enough.
metadata:
  memory_tags:
    - domain:social-media
    - workflow:trend-lifecycle
    - skill_role:researcher
    - repo_boundary:tools
    - inputs:public-shortform-evidence
    - outputs:trend-lifecycle-case
    - risk:medium
---

# Short-Form Trend Lifecycle Ops

## Trigger

Use when:

- someone asks who started a short-form format, how long it has been spreading,
  whether it peaked, or whether it is still worth adapting;
- a sweep finds one ultra-viral post and needs to test whether it is a portable
  cross-creator format rather than a one-account outlier;
- a trend-guide site, provider feed, watchlist, or creator credit supplies a
  promising candidate that needs source-backed verification;
- the result should become a durable, comparable trend case.

Do not use for general news heat, one creator's content audit, or a topic that
has no reproducible video grammar. Use an ordinary market/news radar for those.

## Inputs

- Required: one candidate post, trend-guide page, repeated format description,
  or discovery query.
- Required for durable logging: a caller-supplied private `trend_root`.
- Optional: target audience, adaptation boundary, platform priority, existing
  provider exports, previous metric snapshots, and known creator credits.

Read [case-schema.md](references/case-schema.md) before creating or validating a
case. Read [discovery-sources.md](references/discovery-sources.md) when choosing
collection surfaces or evaluating a provider/repository.

## Core Distinction

Keep these jobs separate:

1. **Discovery nominates candidates.** A provider, trend-guide site, feed,
   watchlist, or outlier search can say "inspect this."
2. **Lifecycle research verifies the wave.** It establishes format match,
   lineage, independent replication, dated performance evidence, and current
   state.

Never promote a provider's label such as `rising`, `viral`, or `trending` into
the lifecycle conclusion without inspectable evidence.

## Workflow

### 1. Define the exact format grammar

Write a subject-free grammar before searching. Include the observable hook,
beat structure, progression rule, visual/audio device, and payoff. Also write:

- `included`: what must be present to count;
- `excluded`: nearby topics, sounds, or aesthetics that do not share the
  grammar;
- `parent_family`: a broader ancestor, if one exists;
- `mutation_boundary`: what changed in the candidate.

A changing topic does not make a new format. Shared keywords do not prove the
same format.

### 2. Initialize the durable case

Run:

```bash
python3 scripts/init_trend_case.py \
  --root <trend_root> \
  --slug <subject-free-slug> \
  --title "<human title>" \
  --discovered-on YYYY-MM-DD
```

This creates one folder per trend, a case template, an append-only evidence
file, and a row in the root index. Do not overwrite an existing case.

### 3. Collect discovery candidates broadly

Use at least two different candidate surfaces when available:

- trend-guide or provider feed;
- keyword, caption, hashtag, sound, or account search;
- explicit `inspired by`, tag, remix, stitch, or caption credit;
- creator-relative outlier scan;
- cross-platform search for the exact grammar;
- a bounded export from an approved API or data provider.

Preserve canonical post URLs. Provider rows without a canonical URL are leads,
not case evidence.

### 4. Establish lineage without inventing an inventor

Search backward from the candidate through explicit credit edges, older exact
grammar matches, and plausible ancestors. Label each item as one of:

- `source_candidate`;
- `breakout_mutation`;
- `independent_copy`;
- `parent_ancestor`;
- `negative_control`.

Report **earliest source-backed post found in the bounded search** unless an
inventor claim is independently proven. Similarity is not a credit edge.

### 5. Build the replication census

Count both posts and unique creators. Treat repeated episodes by one creator as
one creator series, not multiple independent adoptions. Deduplicate known
cross-platform reposts.

The default copy-wave confirmation gate is at least three independent creators
matching the exact grammar. Below that, label the wave `unconfirmed` even if one
post is enormous.

### 6. Preserve time correctly

Append one JSON object per observed post or snapshot to `evidence.jsonl`.
Always record `published_at` and `observed_at` separately. Use `null` for
unavailable metrics.

Do not infer historical velocity from today's lifetime counter. Peak and decay
require comparable cohorts, repeated snapshots, dated search results, or an
explicitly bounded proxy with its limitation stated.

### 7. Assign lifecycle milestones

Use these definitions:

- `onset`: earliest exact-grammar source-backed instance found;
- `breakout`: first defensible absolute breakout or large creator-relative
  lift;
- `copy_wave_onset`: first interval with at least three independent creators;
- `peak`: strongest supported interval for new creators, matched-post volume,
  and age-adjusted performance—not simply the largest lifetime view count;
- `decay_onset`: at least two later cohorts or snapshots show falling new-
  creator velocity, matched-post volume, or age-adjusted performance;
- `current_stage`: `seed`, `emerging`, `accelerating`, `peaking`, `saturating`,
  `decaying`, `dormant`, `reviving`, `platform-split`, or `unknown`.

Separate same-creator novelty decay from cross-creator wave decay.

### 8. Estimate the remaining usable window

Choose one action label and explain the evidence:

- `act-now`: confirmed wave is rising or accelerating and copy density remains
  low;
- `adapt-with-mutation`: wave is peaking or in early decay, but the portable
  mechanism can still support a differentiated version;
- `watch`: promising seed with insufficient independent replication;
- `direct-copy-exhausted`: saturation or late decay makes a surface copy weak;
- `unknown`: collection gaps prevent a defensible estimate.

Give a bounded calendar window only when the evidence supports one. State what
new evidence would shorten, extend, or reopen it.

### 9. Write the decision, not just the archaeology

Complete `case.md` with:

- observed evidence separated from inference;
- lifecycle card and confidence per milestone;
- lineage and independent-copy census;
- current usable-window decision;
- portable mechanism versus surface elements to reject;
- collection receipt and known coverage gaps.

Update the root `INDEX.md` row if the stage or decision changes.

### 10. Validate

Run:

```bash
python3 scripts/validate_trend_case.py <trend_case_folder>
```

Fix every error before calling the case durable. Warnings are allowed only when
the missing evidence is explicitly recorded in the case.

## Ultra-Viral Escalation Gate

Escalate a candidate from an ordinary sweep into this workflow when either is
true:

- one post has extreme absolute reach and at least two plausible independent
  format matches; or
- three independent creators show the same grammar, at least two clear a
  declared high-reach floor, and at least one clears the declared platform-
  specific ultra-viral absolute threshold.

Do not use a low-follower multiplier alone. The purpose is to find portable
format waves, not merely respectable small-account outliers.

## Outputs

```text
<trend_root>/
  INDEX.md
  YYYY-MM-DD_<trend-slug>/
    case.md
    evidence.jsonl
```

Create `snapshots/` only when actual screenshots, transcripts, or provider
exports need preservation. Do not create empty placeholder folders.

## Boundaries

- The skill is reusable and contains no private handles, account ids,
  credentials, or user-specific defaults.
- Real creator cases, private adaptation strategy, and account-performance
  context belong in the caller's private repository.
- Respect platform access controls, provider terms, rate limits, and privacy.
- Do not bypass authentication or rotate personal accounts to evade limits.
- Do not like, follow, comment, message, publish, purchase, or schedule during
  research.
- Do not adopt external repository code until its license and exact reusable
  component have been reviewed.
