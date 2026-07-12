---
name: x-post-ops
description: Automate daily X (Twitter) posting by synthesizing content from journal summaries and optimizing for 2026 virality algorithm.
memory_tags:
  - domain:social-media
  - workflow:content-generation
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - platform:x-twitter
  - risk:medium
---

# X Post Ops

## Trigger

Use this skill when:
- the user wants to "figure out a post for today"
- automating daily social media presence
- synthesizing X-ready content from latest journal MILESTONES or HIGHLIGHTS
- managing X posting via the `bird` CLI

## Workflow

1. **Information Extraction:**
   - Resolve the private repo with `--private-repo`,
     `LIFEREPO_PRIVATE_ROOT`, or `PRIVATE_REPO_ROOT`; never assume a specific
     repo name or home directory.
   - By default, locate the current day's summary at
     `<private-repo>/journal/summaries/YYYY/MM/YYYY-MM-DD_Summary.md`.
   - For reusable or fixture-based runs, pass `--summary-path` and optional
     `--feed-path`; the equivalent environment variables are
     `X_POST_SUMMARY_PATH` and `X_POST_FEED_PATH`.
   - Parse `## Conversation Milestones` or `## Highlights`.
2. **Draft Generation:**
   - Execute `python3 skills/x-post-ops/scripts/generate_x_posts.py --private-repo <private-repo>`.
   - Ensure drafts follow the **2026 Viral Framework** (Strong hook, high shareability, no external links in body).
3. **User Approval:**
   - Present 3-5 variants to the user.
4. **Publishing:**
   - Resolve Bird credentials from `--token-file`, `X_TWITTER_TOKEN_FILE`, or
     `<private-repo>/.tokens/x-twitter.env`. Existing process environment
     credentials are preserved when no token file is configured.
   - Upon approval, execute `python3 skills/x-post-ops/scripts/post_to_x.py --private-repo <private-repo> --tweet "<content>"`.
   - **Stealth Mode (Recommended)**: If encountering "Error 226" (bot detection), use the `--stealth` flag to post via AppleScript and Chrome:
     `python3 skills/x-post-ops/scripts/post_to_x.py --stealth --tweet "<content>"`

## Guardrails

- **Auth check:** Verify `bird` authentication via `bird whoami` before attempting to post.
- **Portable credentials:** Never assume credentials live under a particular
  user's home directory. Keep token values out of commands, logs, and output.
- **Privacy:** Do not include sensitive information or private keys in the public tweet content.
- **Suppression avoidance:** Place links in the first reply of the post, NOT the main body.

## Tools

- `npx @steipete/bird`: Core CLI for X interactions.
