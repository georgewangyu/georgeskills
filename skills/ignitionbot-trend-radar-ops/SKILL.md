---
name: ignitionbot-trend-radar-ops
description: Run IgnitionBot, a self-contained trend radar CLI, to produce scored morning or ad hoc trend briefs across developer, social, video, RSS, web, and watchlist sources. Use when the user asks for an IgnitionBot sweep, ignition score, morning traction radar, Google-Trends-like score, trend watchlist, or cross-source research brief.
memory_tags:
  - domain:trend-research
  - workflow:morning-radar
  - source:multi-source
  - outputs:scored-brief
---

# IgnitionBot Trend Radar Ops

Use this skill when the task should run the IgnitionBot CLI rather than manually
checking each source. IgnitionBot is expected to be either installed on `PATH`
or available as a source checkout pointed to by `IGNITIONBOT_DIR`.

## Inputs

- Query or query list, such as `AI agents`, `developer tools`, or
  `creator workflow automation`.
- Optional source list: `youtube`, `github`, `hackernews`, `reddit`, `rss`,
  `web`, `tiktok`, `instagram`, `x`.
- Optional window: `24h`, `7d`, `30d`.
- Optional output format: `markdown` or `json`.
- Optional watchlist management request.

## Workflow

1. Check availability:

```bash
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py doctor
```

2. Run a sweep. Prefer explicit queries when the user gives them:

```bash
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py sweep \
  --query "AI agents" \
  --window 30d \
  --sources github,hackernews,reddit \
  --format markdown
```

3. For recurring topics, use the watchlist:

```bash
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py watchlist add "AI agents"
python3 skills/ignitionbot-trend-radar-ops/scripts/run_ignitionbot.py watchlist list
```

4. Summarize the brief by leading with:
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
- Suggested follow-up sweep only when it directly improves the user's stated
  research goal.

## Guardrails

- Do not hardcode local paths. Use `IGNITIONBOT_DIR` or an installed
  `ignitionbot` executable.
- Do not paste private database paths, credentials, or local config values into
  the response.
- If optional sources are missing credentials, report that as source coverage,
  not as a failure.
- Keep the answer focused on trend evidence and actions, not raw JSON dumps,
  unless the user explicitly asks for JSON.
