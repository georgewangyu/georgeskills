# Niche Watchlist Config Contract

Use this schema for private JSON configs. Store real configs in the user's private repo, not in this skill.

```json
{
  "niche": "software engineer creator content",
  "lanes": [
    "software engineer on call",
    "software engineer paycheck budget"
  ],
  "watchlist": [
    {
      "platform": "tiktok",
      "handle": "examplecreator",
      "notes": "Why this creator matters"
    },
    {
      "platform": "youtube",
      "handle": "Example Channel",
      "notes": "Why this channel matters"
    },
    {
      "platform": "instagram",
      "handle": "examplecreator",
      "notes": "Known Instagram creator to poll with igbot private-profile"
    }
  ],
  "thresholds": {
    "max_base": 250000,
    "min_views": 10000,
    "days": 365,
    "max_age_days": 14,
    "limit_per_lane": 10,
    "tiktok_backend": "auto"
  },
  "bot_dirs": {
    "youtube": "<path-to-youtubebot>",
    "tiktok": "<path-to-tiktokbot>",
    "instagram": "<path-to-igbot>"
  }
}
```

Fields:

- `niche`: short description used in final synthesis.
- `lanes`: search phrases for regular targeted sweeps.
- `watchlist`: creator handles/channels to check or use as query seeds.
- `thresholds.max_base`: follower/subscriber cap.
- `thresholds.min_views`: minimum views for candidates.
- `thresholds.days`: YouTube recency window.
- `thresholds.max_age_days`: output filter for recent-only requests, such as the last 14 days.
- `thresholds.limit_per_lane`: result count per lane/platform.
- `thresholds.tiktok_backend`: optional `auto`, `python`, or `node` override for TikTok web collection.
- `bot_dirs`: optional explicit bot paths; env vars can also supply these. Use `instagram` or `ig` for `igbot`.
