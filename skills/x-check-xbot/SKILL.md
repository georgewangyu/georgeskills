---
name: x-check-xbot
description: Check X/Twitter using the native 100% browserless xbot engine. Use for fast, stealthy, direct API fetches of For You and Following feeds.
memory_tags:
  - domain:social-media
  - workflow:timeline-check
  - skill_role:researcher
  - repo_boundary:tools
  - engine:xbot-native
  - risk:medium
---

# X Check Xbot (Native)

## Trigger

Use when:
- the user says `check X`, `check my feed`, or `what's interesting on X`
- you need a fast, browserless fetch that bypasses bot detection
- you want to check the "For You" (home) or "Following" (latest) timelines

## Workflow

1. Use the native xbot CLI:
   - `node xbot/src/cli.js home --count 10`
   - `node xbot/src/cli.js latest --count 10`
   - `node xbot/src/cli.js user <handle>`
2. Tokens are sourced from `georgerepo/.tokens/x-twitter.env`.
3. Summarize high-signal themes.
