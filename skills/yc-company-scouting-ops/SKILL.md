---
name: yc-company-scouting-ops
description: Scout YC companies, batches, and Launch YC signals for standout startups and market patterns.
memory_tags:
  - domain:startup-research
  - source:y-combinator
  - workflow:company-scouting
  - skill_role:researcher
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

1. Define the candidate universe before ranking:
   - Record the batch/category/status filters, fetch time, and official YC surfaces included.
   - For a batch scan, enumerate the complete matching YC Companies directory result set; for a launch scan, enumerate the bounded Launch YC window.
   - Do not let companies encountered on X, Hacker News, or third-party lists silently become the whole universe.
2. Fetch current data from primary YC surfaces first:
   - YC Companies directory for company, batch, industry, description, founder, status, and website data.
   - Launch YC for launch posts and public launch positioning when available.
3. Resolve canonical records:
   - Link each shortlisted company to its official YC company record and company website.
   - Cluster renamed companies, duplicate launch posts, and multiple products from the same event rather than double-counting them.
4. Add secondary context only when useful:
   - company website
   - founder/company X or LinkedIn
   - Hacker News launch/comment threads
   - YCDB, YC Trends, or other public batch-analysis sites as secondary summaries
5. Identify "doing well" cautiously. Use public proxies rather than pretending to know revenue:
   - recently launched with clear positioning
   - strong HN/Product Hunt/X discussion
   - fast hiring, credible customers, funding news, or visible usage
   - repeated category pattern across a batch
   - unusually sharp wedge or distribution advantage
6. Cluster companies by:
   - buyer and user
   - workflow/job-to-be-done
   - wedge type
   - category density in the batch
   - overlap with the user's current projects or interests
7. Run a coverage gate before the short read:
   - Confirm every company above the chosen launch/traction/category threshold was shortlisted or explicitly omitted.
   - Record omitted high-signal companies and a reason such as `duplicate`, `off-scope`, `insufficient current evidence`, or `already covered`.
   - Label directory pagination, unavailable Launch YC pages, stale company metadata, and blocked secondary sources as source gaps.
8. Produce a short read:
   - standout companies
   - batch themes
   - suspiciously crowded categories
   - ideas worth studying or adapting
   - companies to follow on X/HN/Product Hunt if public signals matter
9. If the user asks for durable tracking, save a dated note in the private repo, for example:
   - `<private-repo>/captures/startups/yc/trends/YYYY-MM-DD.md`

## Outputs

- A ranked shortlist of interesting YC companies with source links.
- A batch/category theme summary.
- A "why this matters" read for product ideas, content, or market selection.
- Caveats around evidence quality and which signals are only proxies.
- Snapshot scope, source gaps, and a compact omitted-candidate audit.

## Source Guidance

- Prefer official YC surfaces for company and batch facts.
- Treat third-party YC databases and analysis sites as helpful indexes, not canonical truth.
- Always date the scan because YC batches, launches, and company metadata change.

## Boundaries

- Public specs live in `liferepo`.
- Private notes and saved snapshots live in `<private-repo>`.
- This skill only owns reusable scouting behavior.
- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
