---
name: yc-company-scouting-ops
description: Scout Y Combinator companies, batches, Launch YC posts, and related public signals to identify interesting startups, strong wedges, fast-growing categories, and ideas worth studying. Use when the user asks to check YC, scan YC batches, find interesting YC companies, or understand what is doing well in YC.
memory_tags:
  - domain:startup-research
  - source:y-combinator
  - workflow:company-scouting
  - repo_boundary:tools
  - risk:low
---

# YC Company Scouting Ops

## Trigger

Use when:
- the user asks to check YC, Y Combinator, Launch YC, or a YC batch
- the user wants to find interesting YC companies, standout wedges, or batch themes
- the user wants a Product Hunt or X-style summary of what is happening in YC
- the user wants to compare YC companies by category, batch, market, traction proxy, or idea fit

Do not use when:
- the task is general market sizing; use `market-landscape-research-ops`
- the task is revenue estimation from public signals; use `revenue-signal-research-ops`
- the task is naming or wedge selection after research is already done; use `naming-ops` or `idea-wedge-selection-ops`

## Inputs

- Required: target scope, such as latest batch, a specific batch, category, company, market, or "what is interesting right now."
- Optional: filters for AI, devtools, vertical SaaS, healthcare, fintech, consumer, local services, content tools, or personal usefulness.

## Workflow

1. Fetch current data from primary YC surfaces first:
   - YC Companies directory for company, batch, industry, description, founder, status, and website data.
   - Launch YC for launch posts and public launch positioning when available.
2. Add secondary context only when useful:
   - company website
   - founder/company X or LinkedIn
   - Hacker News launch/comment threads
   - YCDB, YC Trends, or other public batch-analysis sites as secondary summaries
3. Identify "doing well" cautiously. Use public proxies rather than pretending to know revenue:
   - recently launched with clear positioning
   - strong HN/Product Hunt/X discussion
   - fast hiring, credible customers, funding news, or visible usage
   - repeated category pattern across a batch
   - unusually sharp wedge or distribution advantage
4. Cluster companies by:
   - buyer and user
   - workflow/job-to-be-done
   - wedge type
   - category density in the batch
   - overlap with the user's current projects or interests
5. Produce a short read:
   - standout companies
   - batch themes
   - suspiciously crowded categories
   - ideas worth studying or adapting
   - companies to follow on X/HN/Product Hunt if public signals matter
6. If the user asks for durable tracking, save a dated note in the private repo, for example:
   - `<private-repo>/notes-private/startups/yc/trends/YYYY-MM-DD.md`

## Outputs

- A ranked shortlist of interesting YC companies with source links.
- A batch/category theme summary.
- A "why this matters" read for product ideas, content, or market selection.
- Caveats around evidence quality and which signals are only proxies.

## Source Guidance

- Prefer official YC surfaces for company and batch facts.
- Treat third-party YC databases and analysis sites as helpful indexes, not canonical truth.
- Always date the scan because YC batches, launches, and company metadata change.

## Boundaries

- Public specs live in `liferepo`.
- Private notes and saved snapshots live in `<private-repo>`.
- This skill only owns reusable scouting behavior.
- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
