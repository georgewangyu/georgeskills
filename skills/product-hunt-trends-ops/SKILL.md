---
name: product-hunt-trends-ops
description: Scout Product Hunt launches for products, positioning patterns, and market signals.
memory_tags:
  - domain:product-research
  - source:product-hunt
  - workflow:trend-scouting
  - skill_role:researcher
  - repo_boundary:tools
  - risk:low
---

# Product Hunt Trends Ops

## Trigger

Use when:
- the user asks to check Product Hunt or Product Hunt launches
- the user wants to find new products, SaaS ideas, launch patterns, or market signals from Product Hunt
- the user wants to compare winners, top launches, comments, makers, tags, positioning, or traction signals

Do not use when:
- the task is general social-media trend checking; use the relevant platform skill
- the task is revenue estimation from broader commercial evidence; use `revenue-signal-research-ops`
- the task is low-base breakout research across many channels; use `breakout-signal-research-ops`

## Inputs

- Required: target window or category, such as today, this week, AI tools, developer tools, productivity, B2B SaaS, or consumer apps.
- Optional: number of products, comparison criteria, whether to prioritize personal usefulness, business ideas, outreach leads, or content angles.

## Workflow

1. Define the candidate universe before ranking:
   - Record the target date/window, category or topic filters, fetch time, and Product Hunt surfaces included.
   - For a daily or category scan, collect the complete visible ranked set (or all API results in the bounded query), not only launches already known from social posts.
   - If pagination, login, API limits, or unavailable categories truncate the universe, record that as a source gap.
2. Browse current Product Hunt pages or an available Product Hunt API path. This data changes daily, so always fetch fresh data.
3. Collect a compact launch set:
   - product name and URL
   - tagline and category/tags
   - rank, votes, comments, and launch date when visible
   - maker/company context when relevant
4. Resolve each shortlisted launch to its canonical Product Hunt page and, when claims need confirmation, the official product or maker page. Treat roundups and social reactions as discovery context rather than rank evidence.
5. Separate signal from launch hype:
   - Treat votes as attention, not revenue or retention.
   - Prefer launches with specific positioning, clear user pain, and thoughtful comments.
   - Discount generic AI wrappers unless the workflow, distribution, or wedge is unusually sharp.
6. Cluster findings by job-to-be-done, buyer, workflow, and distribution channel. Merge duplicate/relaunched listings when they represent the same product event.
7. Run a coverage gate before publishing the shortlist:
   - Confirm every launch above the chosen rank/vote/comment threshold was either included or intentionally omitted.
   - Record omitted high-signal launches with a short reason such as `duplicate`, `off-scope`, `weak evidence`, or `already tracked`.
8. Call out:
   - personally useful tools worth trying
   - product ideas or wedge patterns worth stealing
   - outbound or content angles
   - weak signals that should not drive decisions yet
9. If the user asks for durable tracking, save a dated note in the private repo, for example:
   - `<private-repo>/captures/social-media/product-hunt/trends/YYYY-MM-DD.md`

## Outputs

- A short ranked list of interesting launches.
- A cluster read: what Product Hunt builders are shipping right now.
- Clear next actions: try, track, ignore, research deeper, or convert into content/outreach.
- Snapshot scope, source gaps, and a compact omitted-candidate audit.

## Source Guidance

- Prefer Product Hunt pages and official Product Hunt API surfaces when available.
- Use secondary sources only for context, not as the source of rank or launch metrics.
- Include fetch date and URLs when saving notes.

## Boundaries

- Public specs live in `liferepo`.
- Private notes and saved snapshots live in `<private-repo>`.
- This skill only owns reusable scouting behavior.
- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
