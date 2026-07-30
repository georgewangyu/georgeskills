---
name: account-video-watchlist-ops
description: Track a private markdown watchlist of niche creator accounts across YouTube, TikTok, and Instagram, then surface new or newly viral videos above an absolute view threshold for format emulation.
metadata:
  memory_tags:
    - domain:video
    - workflow:account-watchlist
    - skill_role:researcher
    - repo_boundary:tools
    - inputs:public-social-account
    - outputs:watchlist-record
    - risk:medium
---

# Account Video Watchlist Ops

## Purpose

Use this skill when the user wants to monitor specific creator accounts in a niche, check whether they posted new videos, and identify high-view or fast-moving posts worth studying.

This is account tracking, not broad search. For keyword sweeps, use `niche-video-watchlist-ops` or `video-breakout-research-ops`.

## Inputs

- Private markdown watchlist path with account rows. See `references/watchlist-format.md`.
- Bot directories for the collectors:
  - `--youtube-bot-dir` or `YOUTUBEBOT_DIR`
  - `--tiktok-bot-dir` or `TIKTOKBOT_DIR`
  - `--ig-bot-dir` or `IGBOT_DIR`
- Thresholds:
  - Default `min_views`: `100000`
  - Optional `max_age_days`, `limit_per_account`, and `timeout_seconds`
- Optional previous JSONL run for `is_new` comparison.

Keep real handles, private notes, and saved run outputs in the user's private repo. Do not hardcode them in this skill.

## Workflow

1. Load the private watchlist.
   - It should be a markdown table with at least `platform` and `handle`.
   - If no watchlist exists, create one in the private repo using the reference format.
2. Run account checks with `scripts/run_account_video_watchlist.py`.
   - YouTube: searches Shorts using `query` when present, otherwise the account/channel handle as the query seed. Treat these as search-seeded candidates unless the result creator matches the intended channel.
   - TikTok: uses public web search for the handle/account seed.
   - Instagram: uses `igbot private-profile` for known profiles.
   - The wrapper passes `--mute-audio true` to TikTok browser automation by default; keep this default unless the user explicitly asks for audio review.
   - Write `--health-out` on scheduled runs. The receipt distinguishes
     `success`, `degraded`, `unavailable`, and `not_attempted` per platform.
   - Keep the default platform circuit breaker. After two consecutive account
     failures, skip the remaining accounts on that platform instead of
     repeating a broken collector for the full watchlist.
   - TikTok `auto` collection retries a failed account once through the Node
     backend by default. Disable this only when a caller has already completed
     an equivalent canary.
3. Rank and filter.
   - Default to `views >= 100000`.
   - Prefer absolute views first, then account-relative outlier signals when available.
   - Mark rows as `is_new` when a previous run is provided.
4. Report.
   - Lead with `watch-first` links, not a giant dump.
   - Include platform, account, views, age, title/caption, URL, and why it is worth studying.
   - Call out collector failures per platform instead of hiding them.

## Quick Command

```bash
python3 skills/account-video-watchlist-ops/scripts/run_account_video_watchlist.py \
  --watchlist <private-repo>/areas/social-media/video/watchlists/niche-accounts.md \
  --youtube-bot-dir <path-to-youtubebot> \
  --tiktok-bot-dir <path-to-tiktokbot> \
  --ig-bot-dir <path-to-igbot> \
  --tiktok-web-backend node \
  --tiktok-web-mute-audio true \
  --health-out /tmp/account-video-watchlist-health.json \
  --min-views 100000 \
  --max-age-days 45 \
  --previous <private-repo>/areas/social-media/video/research/previous-account-watchlist.jsonl \
  --out <private-repo>/areas/social-media/video/research/latest-account-watchlist.jsonl
```

## Output Contract

Return:

- `watch-first`: 5-10 videos above the absolute view threshold.
- `maybe`: videos with good fit but weaker view count, if the user asks for a softer threshold.
- `skip/noise`: accounts or videos that are high-volume but poor fit.
- Per-platform caveats such as TikTok web-search timeout or Instagram login/session failure.
- A machine-readable collector-health receipt for scheduled runs, including
  attempted/succeeded/failed calls, rows returned, fallbacks, circuit-breaker
  skips, and bounded error messages.
- Any account-specific caveats, especially YouTube query drift when a channel-specific collector is unavailable.
- Suggested emulation formats, phrased as reusable structures rather than one-off copies.

## Guardrails

- Do not store real watchlists inside `georgeskills`.
- Do not treat a high multiplier with low views as viral unless the user explicitly asks for low-base breakouts.
- Do not copy creator-specific identity, celebrity access, institution access, or personal-life details that will not transfer.
- If a bot fails, continue with other platforms and report the failure plainly.
- Never overwrite a known-good persistent snapshot with an empty or unavailable
  run. Write a dated attempt first; promote it to `latest` only after the
  health receipt confirms usable rows. A previous snapshot may be referenced
  only with its original collection date and a `stale` label.
- Do not pretend YouTube search-seeded rows are definitely from the tracked account unless the returned creator/channel matches.
- Mute browser automation for media-heavy pages whenever supported; never intentionally play TikTok/Reels/Shorts audio during background research unless the user asks to listen. If TikTok sound is required, require an explicit `--tiktok-web-mute-audio false` override.
