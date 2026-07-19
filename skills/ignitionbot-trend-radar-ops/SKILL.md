---
name: ignitionbot-trend-radar-ops
description: Run IgnitionBot trend sweeps and return scored briefs across configured sources.
memory_tags:
  - domain:trend-research
  - workflow:morning-radar
  - skill_role:researcher
  - repo_boundary:tools
  - source:multi-source
  - outputs:scored-brief
  - risk:medium
---

# IgnitionBot Trend Radar Ops

Use this skill when the task should run the IgnitionBot CLI rather than manually
checking each source. IgnitionBot is expected to be either installed on `PATH`
or available as a source checkout pointed to by `IGNITIONBOT_DIR`.

## Inputs

- Query or query list, such as `AI agents`, `developer tools`, or
  `creator workflow automation`.
- Optional source list: `youtube`, `github`, `producthunt`, `hackernews`,
  `reddit`, `polymarket`, `bluesky`, `digg`, `v2ex`, `rss`, `web`,
  `tiktok`, `instagram`, `x`, `threads`, `pinterest`, `linkedin`,
  `truthsocial`, `exa`, `perplexity`, `jina`, `parallel`, `bilibili`,
  `xiaohongshu`, `douyin`, `wechat`, `weibo`, `xueqiu`, `xiaoyuzhou`.
- Optional window: `24h`, `7d`, `30d`.
- Optional output format: `markdown` or `json`.
- Optional watchlist management request.

## Workflow

1. Define the candidate universe:
   - Record the query list, window, requested sources, fetch time, and any per-source limits.
   - For open-ended sweeps, include at least one canonical discovery surface appropriate to the lane (for example GitHub, Product Hunt, Hacker News, RSS, or web) rather than relying only on personalized/watchlist sources.
   - Treat the configured source/query matrix as the declared universe for this run; a watchlist alone is not a claim about the broader market.

2. Check availability:

```bash
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py doctor
```

3. Run a sweep. Prefer explicit queries when the user gives them:

```bash
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py sweep \
  --query "AI agents" \
  --window 30d \
  --sources github,hackernews,reddit \
  --format markdown
```

4. For recurring topics, use the watchlist:

```bash
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py watchlist add "AI agents"
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py watchlist list
```

5. Resolve canonical primary evidence for each shortlisted cluster:
   - Follow secondary reactions back to the official repository, launch, announcement, or direct discussion page.
   - Merge aliases and duplicate results across sources before comparing scores.

6. Run the coverage gate before summarizing:
   - Compare requested sources with sources actually queried and successful.
   - Audit every cluster above the chosen ignition/traction threshold as included or intentionally omitted.
   - Record omitted clusters with a reason and report unavailable, credential-gated, rate-limited, or empty sources as source gaps rather than zero signal.

7. Summarize the brief by leading with:
   - top clusters by ignition score,
   - source evidence,
   - unavailable sources or credential gaps,
   - next action for each high-signal cluster.

## Output Contract

Return:

- The command run.
- Top scored clusters with traction score, ignition score, confidence, and
  action.
- Evidence links from the generated brief.
- Missing credential/source notes when present.
- The declared candidate universe and a compact omitted-candidate audit for high-signal clusters.
- Suggested follow-up sweep only when it directly improves the user's stated
  research goal.

## Guardrails

- Do not hardcode local paths. Use `IGNITIONBOT_DIR` or an installed
  `ignitionbot` executable.
- Do not paste private database paths, credentials, or local config values into
  the response.
- If optional sources are missing credentials, report that as source coverage,
  not as a failure.
- X reads must use the Bird-style `AUTH_TOKEN` + `CT0` session GraphQL adapter.
  Do not use an X developer bearer token or fall back to the paid official
  recent-search API. Report a stale session or query ID as a source gap.
- Do not promote a secondary reaction without resolving the canonical event
  when a primary source is available.
- Keep the answer focused on trend evidence and actions, not raw JSON dumps,
  unless the user explicitly asks for JSON.
