---
name: x-post-ops
description: Automate daily X (Twitter) posting by synthesizing content from journal summaries and optimizing for 2026 virality algorithm.
memory_tags:
  - domain:social-media
  - workflow:content-generation
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
   - Locate the current day's summary in `georgerepo/journal/summaries/YYYY/MM/YYYY-MM-DD_Summary.md`.
   - Parse `## Conversation Milestones` or `## Highlights`.
2. **Draft Generation:**
   - Execute `python3 skills/x-post-ops/scripts/generate_x_posts.py`.
   - Ensure drafts follow the **2026 Viral Framework** (Strong hook, high shareability, no external links in body).
3. **User Approval:**
   - Present 3-5 variants to the user.
4. **Publishing:**
   - Upon approval, execute `python3 skills/x-post-ops/scripts/post_to_x.py --tweet "<content>"`.
   - **Stealth Mode (Recommended)**: If encountering "Error 226" (bot detection), use the `--stealth` flag to post via AppleScript and Chrome:
     `python3 skills/x-post-ops/scripts/post_to_x.py --stealth --tweet "<content>"`

## Guardrails

- **Auth check:** Verify `bird` authentication via `bird whoami` before attempting to post.
- **Privacy:** Do not include sensitive information or private keys in the public tweet content.
- **Suppression avoidance:** Place links in the first reply of the post, NOT the main body.

## Tools

- `npx @steipete/bird`: Core CLI for X interactions.
