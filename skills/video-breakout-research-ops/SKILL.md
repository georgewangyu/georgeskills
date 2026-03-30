---
name: video-breakout-research-ops
description: Sweep TikTok, Instagram, and YouTube Shorts for low-base, high-traction video patterns, then score follower-to-view asymmetry and cluster portable concepts into a research shortlist.
memory_tags:
  - domain:social-media
  - workflow:breakout-concept-research
  - repo_boundary:tools
  - inputs:niche-brief
  - outputs:concept-shortlist
  - risk:medium
---

# Video Breakout Research Ops

## Trigger

Use when:
- the user wants the creator-content equivalent of a small account with one huge hit
- the task is to research TikTok, Instagram, or YouTube Shorts for asymmetric traction
- the user wants to replace manual FYP scrolling with a repeatable research workflow
- the goal is to extract portable hooks, formats, and concept angles rather than just collect creator links

Do not use when:
- the user only wants to check one handle or one post; use `tiktok-check-ops`, `instagram-check-ops`, or `youtube-check-ops`
- the task is long-form YouTube channel research without Shorts-specific breakout logic
- the user wants private account access, inbox/session management, or a full browser automation buildout

## Inputs

- Required: niche, target platform or platforms, follower cap, and time window
- Optional: region, language, desired output count, seed creators, excluded creators, and whether browser fallback is allowed

## Core Question

Ask:
- which creators still look small relative to the size of their best-performing short-form videos
- which concepts repeat across multiple low-base creators
- which hooks look portable enough to adapt into the user's own niche

## Workflow

1. Define the search frame.
   Normalize:
   - niche and adjacent keywords
   - platform set: TikTok, Instagram, YouTube Shorts
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

## Output Contract

Return:
- a ranked breakout candidate table
- 3 to 10 concept clusters with evidence
- why each cluster likely worked
- portability notes for the user's niche
- false-positive caveats and missing-data caveats
- next concepts to test

## Guardrails

- Do not equate raw views with a useful concept. Small-account asymmetry matters more than absolute size.
- Do not treat scraped public metadata as stable or complete.
- Penalize celebrity transfer, pre-existing fame, or already-large off-platform audiences when visible.
- Separate concept portability from creator charisma.
- Use `playwright` only when public probes are insufficient and visual inspection materially improves the result.

## References

Open only when needed:
- search surfaces and scoring notes: `references/research-patterns.md`
