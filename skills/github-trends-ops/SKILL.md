---
name: github-trends-ops
description: Fetch and analyze GitHub trending repositories (daily/weekly) to surface high-signal development trends.
memory_tags:
  - domain:development
  - workflow:trend-analysis
  - skill_role:researcher
  - repo_boundary:tools
  - source:github-trending
  - risk:low
---

# GitHub Trending Operations

Use this skill to monitor what the open-source community is building in real-time.

## Trigger

Use when:
- the user asks "what's trending on GitHub today?" or "what's big this week?"
- starting the morning debrief to ground daily planning in global developer signals
- performing market research for new product ideas

## Workflow

1.  **Define the candidate universe**:
    -   Record the window (`daily` or `weekly`), language filter, fetch time, and GitHub surfaces included.
    -   For a normal Trending scan, treat the complete fetched Trending page as the minimum candidate universe; do not begin from remembered repositories or a personalized feed.
    -   If the user asks what is broadly breaking out beyond Trending, add explicit GitHub Search/topic/release surfaces and label that expanded scope.
2.  **Fetch Trends**:
    -   Daily: `python3 georgeskills/skills/github-trends-ops/scripts/fetch_github_trends.py --since daily`
    -   Weekly: `python3 georgeskills/skills/github-trends-ops/scripts/fetch_github_trends.py --since weekly`
3.  **Resolve primary sources**:
    -   Open each shortlisted repository and use its canonical repository, README, releases, and linked project documentation for identity and claims.
    -   Cluster renamed, forked, or duplicate implementations instead of counting them as separate trends.
    -   Treat posts and newsletters as discovery context, not as substitutes for the canonical repository.
4.  **Analyze**:
    -   Look for clusters of technology (e.g., "many new AI agents", "rise in Rust-based infra").
    -   Check whether top repositories align with the user's stated projects or research lanes.
    -   Label unavailable language pages, rate limits, failed fetches, or missing historical counters as source gaps rather than zero signal.
5.  **Run the coverage gate before ranking**:
    -   Confirm every repository above the chosen rank/star-growth threshold was either shortlisted or explicitly omitted.
    -   Record a compact omitted-candidate audit with repository, observed signal, and reason (`duplicate`, `off-scope`, `low evidence`, or `already covered`).
6.  **Log**:
    -   Summary is logged to `<private-repo>/captures/social-media/github/trends/YYYY-MM-DD.md`.

## Output Contract

Return the snapshot time and scope, ranked repositories/clusters with canonical
links, the most important source gaps, and the omitted-candidate audit. A scan
is not complete when a high-signal candidate silently disappears between fetch
and ranking.
