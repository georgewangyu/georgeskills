---
name: broad-video-trend-radar-ops
description: Broad cross-platform short-form trend scanning using local YouTube, TikTok, and Instagram bots. Use when the user wants a wider radar of what is popping off beyond their niche, including high-multiplier videos, reusable formats, emerging hooks, broad TikTok/YouTube Shorts/Instagram Reels trends, sounds or music cues when visible, and outside-niche patterns that could be adapted into the user's content.
---

# Broad Video Trend Radar Ops

## Purpose

Run a wide radar sweep across TikTok, YouTube Shorts, and optionally Instagram Reels to find transferable video patterns outside a narrow niche. Prefer this skill when the user asks what is generally trending, wants inspiration from other categories, or wants to find formats to adapt rather than only competitors to monitor.

## Inputs

- Broad themes or categories to inspect, such as comedy, money, lifestyle, work, AI, moving, food, fitness, or relationships.
- Optional platform focus: TikTok, YouTube, Instagram, or all available collectors.
- Optional thresholds: follower/subscriber cap, minimum views, limit, and recency window.
- Bot locations: pass `--youtube-bot-dir`, `--tiktok-bot-dir`, and `--ig-bot-dir`, or set `YOUTUBEBOT_DIR`, `TIKTOKBOT_DIR`, and `IGBOT_DIR`.

## Workflow

1. Pick a broad sweep frame.
   - Use 5-12 lanes spanning adjacent and non-adjacent categories.
   - Include at least one lane outside the user's obvious niche.
2. Run collectors.
   - Use `scripts/run_broad_video_radar.py` when doing a repeatable sweep.
   - Use `tiktokbot web-trending` for TikTok trend/FYP-style candidates.
   - Use `tiktokbot web-search` for broad lanes where keyword context matters.
   - The wrapper passes `--mute-audio true` to TikTok browser automation by default; only disable it for explicit audio review.
   - Use `youtubebot find` for YouTube Shorts-like search lanes.
   - Use `igbot private-search` for Instagram Reels lanes when a private bridge session is available; treat `login_required` as a collector limitation and continue.
3. Rank asymmetry.
   - Prioritize views/base-size multiplier, not raw scale.
   - Keep a few high-raw-view examples only when the format is unusually clear.
4. Cluster by trend mechanism.
   - Hook pattern: curiosity gap, confession, shock stat, POV, social proof.
   - Format: street interview, budget breakdown, skit, green screen, reaction, list.
   - Visual/audio cue: repeated sound, caption pacing, cut pattern, prop, setting.
5. Translate into adaptation notes.
   - Explain what can be borrowed without copying the creator.
   - Name the first testable version for the user's content lane.

## Quick Commands

Run a broad default sweep:

```bash
python3 skills/broad-video-trend-radar-ops/scripts/run_broad_video_radar.py \
  --youtube-bot-dir <path-to-youtubebot> \
  --tiktok-bot-dir <path-to-tiktokbot> \
  --ig-bot-dir <path-to-igbot> \
  --tiktok-mute-audio true \
  --out /tmp/broad-video-radar.jsonl
```

Run with explicit lanes:

```bash
python3 skills/broad-video-trend-radar-ops/scripts/run_broad_video_radar.py \
  --lane "money hacks" \
  --lane "work from home comedy" \
  --lane "moving to a new city" \
  --lane "AI tools" \
  --max-base 300000 \
  --max-age-days 14 \
  --tiktok-mute-audio true \
  --out /tmp/broad-video-radar.jsonl
```

## Output Contract

Return:

- Ranked cross-platform trend candidates with links and multiplier signals.
- Published date and age in days for each video.
- 3-8 trend clusters with evidence links.
- Notes on music/sound when available in captions or visible metadata.
- Adaptation ideas for the user's content lane.
- Caveats about scraping volatility, incomplete TikTok/Instagram sound metadata, Instagram private-session requirements, and raw-view false positives.

## Guardrails

- Do not make this a competitor watchlist; use `niche-video-watchlist-ops` for targeted tracking.
- Do not claim that a sound is trending unless the available metadata or visual review supports it.
- Do not over-index on accounts that are already huge unless the format is unusually portable.
- Prefer links the user can watch quickly over long explanation.
- Keep TikTok browser automation muted during background sweeps unless the user explicitly asks to listen for sound/audio cues.
