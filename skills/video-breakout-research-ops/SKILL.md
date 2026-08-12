---
name: video-breakout-research-ops
description: Research low-base video breakouts and follower-conversion outliers across TikTok, Instagram, and YouTube without confusing attention with audience conversion.
memory_tags:
  - domain:social-media
  - workflow:breakout-concept-research
  - skill_role:researcher
  - repo_boundary:tools
  - inputs:niche-brief
  - outputs:concept-shortlist
  - risk:medium
---

# Video Breakout Research Ops

## Trigger

Use when:
- the user wants the creator-content equivalent of a small account with one huge hit
- the task is to research TikTok, Instagram, YouTube Shorts, or long-form YouTube for asymmetric traction
- the user wants to find posts that converted disproportionate reach into followers
- the user wants to replace manual FYP scrolling with a repeatable research workflow
- the goal is to extract portable hooks, formats, and concept angles rather than just collect creator links

Do not use when:
- the user only wants to check one handle or one post; use `tiktok-check-ops`, `instagram-check-ops`, or `youtube-check-ops`
- the user wants private account access, inbox/session management, or a full browser automation buildout

## Inputs

- Required: niche, target platform or platforms, follower cap, and time window
- Optional: region, language, desired output count, seed creators, excluded creators, and whether browser fallback is allowed

## Core Question

Ask:
- which creators still look small relative to the size of their best-performing short-form videos
- which concepts repeat across multiple low-base creators
- which hooks look portable enough to adapt into the user's own niche
- which posts converted attention into durable audience growth, with what evidence and CTA contamination

## Workflow

1. Define the search frame.
   Normalize:
   - niche and adjacent keywords
   - platform set: TikTok, Instagram, YouTube Shorts, long-form YouTube
   - low-base threshold such as `<25k followers`
   - recency window such as `last 30 days`
2. Gather candidate creators and posts.
   Use the existing account-check skills for single-target probes when you already have handles. For broader sweeps, use search, lightweight public probes, or browser review to gather a worksheet with:
   - platform
   - creator_handle
   - followers
   - video_id or post_url
   - post_age_days
   - views
   - likes
   - comments
   - shares if visible
   - reach or accounts_reached if available
   - follows attributed to the post if available
   - saves if visible
   - duration_seconds and avg_watch_seconds if available
   - profile_continuity, series_open_loop, and topic_profile_fit assessments
   - cta_type and attribution provenance
   - hook_text
   - concept_summary
3. Score asymmetry first, then quality.
   Default breakout heuristic:
   - `asymmetry_score = log10(max_views + 1) - log10(max(followers, 1) + 1)`
   Adjust with:
   - repeatability bonus when the creator has more than one outsized post
   - recency bonus for fresh wins
   - portability bonus when the concept can transfer outside the creator's identity
   - credibility bonus when the account genuinely appears small
   - saturation penalty when the format looks overfished
4. Separate signal from noise.
   Split findings into:
   - one-off viral accidents
   - repeatable concept winners
   - identity-driven creators whose results are not portable
5. Cluster by concept.
   Group winners by:
   - hook pattern
   - content structure
   - visual or editing format
   - audience promise
6. Deliver concepts, not just accounts.
   The final output should rank concept patterns and include example creators as evidence, not as the main artifact.
7. Run follower-conversion analysis as a separate lane when post-attributed follow data exists.
   Track conversion strength independently from evidence confidence:
   - `follows_per_view = follows / views`
   - `follows_per_reach = follows / reach`
   - `avg_watch_percentage = avg_watch_seconds / duration_seconds`
   - `saves_per_view = saves / views`
   - `shares_per_view = shares / views`
   - profile continuity: does the profile clearly promise more of what the post delivered?
   - series/open-loop design: is there an honest reason to return?
   - topic-to-profile fit: are new followers likely to value the normal feed?
   - CTA type: `none`, `implicit_series`, `direct_follow`, `keyword_dm`, or `follow_gated_asset`
   - attribution: platform first-party, creator first-party, public metadata, inferred, or unknown
8. Interpret follower conversion conservatively.
   A keyword-DM or follow-gated asset can produce real attributed follows, but it does not prove that the content alone earned them. Label the result as hybrid or funnel-contaminated instead of subtracting an invented amount. Never use a creator's current follower count as the historical pre-post base unless the historical value is evidenced.

## Script Surface

Use `scripts/score_video_breakouts.py` when you already have a CSV or JSONL worksheet of sampled creators/posts and want a ranked markdown shortlist.

Expected columns or keys:
- `platform`
- `creator_handle`
- `followers`
- `views`
- `likes` optional
- `comments` optional
- `shares` optional
- `reach` or `accounts_reached` optional
- `follows` optional
- `saves` optional
- `duration_seconds` optional
- `avg_watch_seconds` optional
- `profile_continuity` optional (`0-1`, or `low` / `medium` / `high`)
- `series_open_loop` optional (`0-1`, or `low` / `medium` / `high`)
- `topic_profile_fit` optional (`0-1`, or `low` / `medium` / `high`)
- `cta_type` optional
- `attribution` optional
- `post_age_days` optional
- `hook_text` optional
- `concept_summary` optional
- `post_url` optional

The script computes:
- per-row `asymmetry_score`
- creator-level repeatability
- engagement proxy
- a weighted breakout score
- concept clusters based on normalized hook and concept text
- a separate follower-conversion table when attributed follows are present
- conversion ratios, a signal-strength score, CTA mode, and evidence confidence

## Output Contract

Return:
- a ranked breakout candidate table
- 3 to 10 concept clusters with evidence
- why each cluster likely worked
- portability notes for the user's niche
- false-positive caveats and missing-data caveats
- follower-conversion findings kept separate from view asymmetry
- next concepts to test

## Guardrails

- Do not equate raw views with a useful concept. Small-account asymmetry matters more than absolute size.
- Do not treat scraped public metadata as stable or complete.
- Penalize celebrity transfer, pre-existing fame, or already-large off-platform audiences when visible.
- Separate concept portability from creator charisma.
- Do not infer follower conversion from views, likes, current profile size, or a creator's verbal claim without identifying the evidence class.
- Treat creator-shared platform insights as first-party evidence supplied by the creator, not independently audited data.
- Keep content-driven conversion distinct from direct-follow, keyword-DM, and follow-gated conversion.
- Prefer ethical adaptations: deliver value before the CTA, make the profile promise continuous with the post, disclose what a keyword response does, and do not require a follow to unlock a promised resource.
- Reject deceptive scarcity, hidden follow gates, and forced engagement as adaptation patterns even when the numbers are strong.
- Use `playwright` only when public probes are insufficient and visual inspection materially improves the result.

## References

Open only when needed:
- search surfaces and scoring notes: `references/research-patterns.md`
