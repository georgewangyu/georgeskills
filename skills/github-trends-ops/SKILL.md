---
name: github-trends-ops
description: Fetch and analyze GitHub trending repositories (daily/weekly) to surface high-signal development trends.
memory_tags:
  - domain:development
  - workflow:trend-analysis
  - source:github-trending
---

# GitHub Trending Operations

Use this skill to monitor what the open-source community is building in real-time.

## Trigger

Use when:
- the user asks "what's trending on GitHub today?" or "what's big this week?"
- starting the morning debrief to ground daily planning in global developer signals
- performing market research for new product ideas

## Workflow

1.  **Fetch Trends**:
    -   Daily: `python3 georgeskills/skills/github-trends-ops/scripts/fetch_github_trends.py --since daily`
    -   Weekly: `python3 georgeskills/skills/github-trends-ops/scripts/fetch_github_trends.py --since weekly`
2.  **Analyze**:
    -   Look for clusters of technology (e.g., "many new AI agents", "rise in Rust-based infra").
    -   Check if any top repos align with the user's current projects (`ADA`, `BitePath`, etc.).
3.  **Log**:
    -   Summary is logged to `<private-repo>/captures/social-media/github/trends/YYYY-MM-DD.md`.
