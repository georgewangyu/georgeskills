---
name: niche-video-watchlist-ops
description: Targeted creator-niche video monitoring using local YouTube and TikTok bots. Use when the user wants to search within a defined content niche, maintain or consult a watchlist of creators/search lanes, find videos from tracked creators that are popping off, save promising links for later review, or turn niche breakout videos into repeatable short-form series ideas.
---

# Niche Video Watchlist Ops

## Purpose

Run focused, repeatable sweeps for a specific creator niche. Prefer this skill when the user already has a content lane, seed creators, recurring keywords, or a watchlist they want monitored.

This skill uses local `youtubebot` and `tiktokbot` checkouts as collectors, then ranks videos by low-base/high-traction signal and groups them into portable concepts.

## Inputs

- Niche brief: the creator lane or audience problem.
- Search lanes: keywords, phrases, hashtags, or formats to run.
- Watchlist: creator handles/channels to track when available.
- Thresholds: follower/subscriber cap, minimum views, limit, recency window.
- Bot locations: pass `--youtube-bot-dir` and `--tiktok-bot-dir`, or set `YOUTUBEBOT_DIR` and `TIKTOKBOT_DIR`.

Keep user-specific watchlists, private handles, and output archives in the user's private repo. Do not hardcode them inside this skill.

## Workflow

1. Load private config if the user has one.
   - Use `references/config-contract.md` for the expected public-safe schema.
   - If no config exists, build a small search plan from the user's prompt.
2. Run targeted search lanes.
   - Prefer `scripts/run_niche_video_sweep.py` for repeatable sweeps.
   - Use YouTube Shorts filters for YouTube.
   - Use `tiktokbot web-search --backend auto` for TikTok.
3. Include watchlist checks when possible.
   - For YouTube, query creator/channel names plus niche keywords if channel-specific commands are not available.
   - For TikTok, query creator handles plus niche keywords; use `tiktok-check-ops` only for one-off account inspection.
4. Rank videos.
   - Favor views/subscribers or views/followers over raw views.
   - Treat creator-baseline outliers as stronger than ratio-only rows when available.
   - Penalize videos whose concept depends on celebrity, institution, or non-transferable personal identity.
5. Save or report.
   - If the user asks to save, write JSONL/Markdown into the private repo or requested output path.
   - Otherwise return a watch list of links grouped by concept.
6. Recommend next review step.
   - Mark videos as `watch-first`, `maybe`, or `probably-noise`.
   - Suggest the 2-4 concept clusters most likely to become a series.

## Quick Commands

Run a niche sweep from inline lanes:

```bash
python3 skills/niche-video-watchlist-ops/scripts/run_niche_video_sweep.py \
  --youtube-bot-dir <path-to-youtubebot> \
  --tiktok-bot-dir <path-to-tiktokbot> \
  --lane "software engineer on call" \
  --lane "software engineer paycheck budget" \
  --max-base 250000 \
  --min-views 10000 \
  --max-age-days 14 \
  --out /tmp/niche-video-sweep.jsonl
```

Run from a private config:

```bash
python3 skills/niche-video-watchlist-ops/scripts/run_niche_video_sweep.py \
  --config <private-repo>/areas/social-media/video-watchlists/example.json \
  --out <private-repo>/areas/social-media/research/latest-niche-sweep.jsonl
```

## Output Contract

Return:

- Ranked video links with platform, creator, views, base size, and multiplier.
- Published date and age in days for each video.
- The search lane or watchlist source that found each video.
- Concept cluster labels and why each might transfer into the user's niche.
- A short `watch order` list, not a giant dump.
- Any missing-data caveats, especially when TikTok only provides ratio signals.

## Guardrails

- Do not store tokens, cookies, or account-specific handles in this skill.
- Do not equate raw views with a good concept.
- Do not overfit to one viral accident; look for repeatability across creators or formats.
- Keep broad trend discovery out of this skill; use `broad-video-trend-radar-ops` for wide, non-niche sweeps.
