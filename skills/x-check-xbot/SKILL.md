---
name: x-check-xbot
description: Check X/Twitter using xbot's browser-session GraphQL reader. Use for fast, browserless fetches of For You, Following, user, and search/outlier surfaces without consuming official X API credits.
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
   - `node xbot/src/cli.js outliers --query <query> --count 20`
2. Read credentials are the Bird-style browser-session values `AUTH_TOKEN` and
   `CT0`, sourced from the configured private environment file.
3. Do not use `api.x.com`, `api.twitter.com`, an X developer Bearer Token, or
   the official recent-search endpoint for routine or automated reads. Never
   fall back from a failed session read to a billable official read. Stop and
   report the session/query-ID blocker instead.
4. Preserve account metrics in the summary. For each high-signal post, include
   the handle/link, author follower count from `authorFollowers` when present,
   reach/views, likes, reposts/replies when available, and a low-follower /
   high-reach note when the ratio is notable.
5. If `authorFollowers` is missing from the fetched item, write `followers
   unavailable` instead of omitting the account metric. The missing field is a
   source-quality signal, not a reason to collapse the item into a generic
   digest.
6. Summarize high-signal themes after the item-level read, not instead of it.
