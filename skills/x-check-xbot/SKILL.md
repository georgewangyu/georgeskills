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
3. Preserve account metrics in the summary. For each high-signal post, include
   the handle/link, author follower count from `authorFollowers` when present,
   reach/views, likes, reposts/replies when available, and a low-follower /
   high-reach note when the ratio is notable.
4. If `authorFollowers` is missing from the fetched item, write `followers
   unavailable` instead of omitting the account metric. The missing field is a
   source-quality signal, not a reason to collapse the item into a generic
   digest.
5. Summarize high-signal themes after the item-level read, not instead of it.
